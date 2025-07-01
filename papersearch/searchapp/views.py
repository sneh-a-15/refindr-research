import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from django.shortcuts import render
from django.conf import settings
from django.contrib import messages
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
import json
from django.contrib.auth.decorators import login_required
import pyrebase

logger = logging.getLogger(__name__)

def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created for {user.username}!")
            return redirect('login')  # Redirect to your home page after successful signup
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            # Redirect to a specific page or the previous page if 'next' is in GET parameters
            if 'next' in request.POST:
                return redirect(request.POST.get('next'))
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

def land(request):
    return render(request, 'landing.html')

def home(request):
    print("DEBUG: request.GET =", dict(request.GET))
    query = request.GET.get('query', '').strip()
    sources = request.GET.getlist('sources')
    print("DEBUG: Selected sources from form:", sources)

    if not sources:
        print("DEBUG: No sources selected, defaulting to ['arxiv']")
        sources = ['arxiv']

    papers = []
    search_stats = {}

    if query and len(query) < 2:
        messages.warning(request, 'Search query must be at least 2 characters long.')
        print("DEBUG: Query too short:", query)
        query = ''

    if query:
        try:
            print("DEBUG: Initiating search with query:", query, "and sources:", sources)
            papers, search_stats = search_multiple_sources(query, sources)
            print("DEBUG: Search stats:", search_stats)
            total_papers = len(papers)
            if total_papers > 0:
                print(f"DEBUG: Found {total_papers} papers from {len([s for s in search_stats.values() if s.get('count', 0) > 0])} sources.")
                messages.success(request, f'Found {total_papers} papers from {len([s for s in search_stats.values() if s.get("count", 0) > 0])} sources.')
            else:
                print("DEBUG: No papers found.")
                messages.info(request, 'No papers found. Try adjusting your search terms or selecting different sources.')
        except Exception as e:
            logger.error(f"Search error: {e}")
            print("DEBUG: Exception during search:", e)
            messages.error(request, 'An error occurred during search. Please try again.')

    available_sources = get_available_sources()
    print("DEBUG: Available sources for checkboxes:", [s['id'] for s in available_sources])
    print("DEBUG: Passing selected_sources to template:", sources)
    print("DEBUG: Passing available_sources to template:", [s['id'] for s in available_sources])

    context = {
        'query': query,
        'papers': papers[:50],
        'selected_sources': sources,
        'available_sources': available_sources,
        'search_stats': search_stats,
        'total_results': len(papers),
        'search_performed': bool(query),
    }
    print("DEBUG: Context for template:", {k: (v if k != 'papers' else f'{len(v)} papers') for k, v in context.items()})
    return render(request, 'home.html', context)

logger = logging.getLogger(__name__)

def get_available_sources():
    sources = []
    if getattr(settings, 'ACADEMIC_APIS', {}).get('ARXIV', {}).get('ENABLED', True):
        sources.append({
            'id': 'arxiv',
            'name': 'arXiv',
            'icon': 'fas fa-archive',
            'description': 'Open access preprints in physics, mathematics, computer science, and more',
            'free': True,
            'rate_limit': 100,
            'quality': 'High',
            'fields': ['Physics', 'Mathematics', 'Computer Science', 'Biology']
        })
    if getattr(settings, 'ACADEMIC_APIS', {}).get('SEMANTIC_SCHOLAR', {}).get('ENABLED', True):
        sources.append({
            'id': 'semantic_scholar',
            'name': 'Semantic Scholar',
            'icon': 'fas fa-brain',
            'description': 'AI-powered academic search with citation analysis',
            'free': True,
            'rate_limit': 100,
            'quality': 'High',
            'fields': ['All Fields']
        })
    if getattr(settings, 'ACADEMIC_APIS', {}).get('GOOGLE_SCHOLAR', {}).get('ENABLED', False):
        api_key = getattr(settings, 'ACADEMIC_APIS', {}).get('GOOGLE_SCHOLAR', {}).get('API_KEY')
        sources.append({
            'id': 'google_scholar',
            'name': 'Google Scholar',
            'icon': 'fab fa-google',
            'description': 'Comprehensive academic search across all disciplines',
            'free': False,
            'rate_limit': 100,
            'quality': 'Very High',
            'fields': ['All Fields'],
            'configured': bool(api_key)
        })
    if getattr(settings, 'ACADEMIC_APIS', {}).get('IEEE_XPLORE', {}).get('ENABLED', False):
        api_key = getattr(settings, 'ACADEMIC_APIS', {}).get('IEEE_XPLORE', {}).get('API_KEY')
        sources.append({
            'id': 'ieee_xplore',
            'name': 'IEEE Xplore',
            'icon': 'fas fa-microchip',
            'description': 'Premier source for engineering and technology research',
            'free': False,
            'rate_limit': 200,
            'quality': 'Very High',
            'fields': ['Engineering', 'Computer Science', 'Technology'],
            'configured': bool(api_key)
        })
    if getattr(settings, 'ACADEMIC_APIS', {}).get('SPRINGER', {}).get('ENABLED', False):
        api_key = getattr(settings, 'ACADEMIC_APIS', {}).get('SPRINGER', {}).get('API_KEY')
        sources.append({
            'id': 'springer',
            'name': 'Springer Nature',
            'icon': 'fas fa-book-open',
            'description': 'Leading publisher of scientific, scholarly and professional content',
            'free': False,
            'rate_limit': 5000,
            'quality': 'Very High',
            'fields': ['Science', 'Technology', 'Medicine', 'Humanities'],
            'configured': bool(api_key)
        })
    if getattr(settings, 'ACADEMIC_APIS', {}).get('ELSEVIER', {}).get('ENABLED', False):
        api_key = getattr(settings, 'ACADEMIC_APIS', {}).get('ELSEVIER', {}).get('API_KEY')
        sources.append({
            'id': 'elsevier',
            'name': 'Elsevier/Scopus',
            'icon': 'fas fa-graduation-cap',
            'description': 'World\'s largest abstract and citation database',
            'free': False,
            'rate_limit': 20000,
            'quality': 'Exceptional',
            'fields': ['All Fields'],
            'configured': bool(api_key)
        })
    return sources

def search_multiple_sources(query, sources, max_results_per_source=15):
    all_papers = []
    search_stats = {}
    search_functions = {
        'arxiv': search_arxiv_papers,
        'semantic_scholar': search_semantic_scholar,
        'google_scholar': search_google_scholar,
        'ieee_xplore': search_ieee_xplore,
        'springer': search_springer,
        'elsevier': search_elsevier
    }
    valid_sources = [s for s in sources if s in search_functions]
    if not valid_sources:
        return [], {'error': 'No valid sources selected'}
    with ThreadPoolExecutor(max_workers=min(len(valid_sources), 6)) as executor:
        future_to_source = {}
        for source in valid_sources:
            print(f"DEBUG: Submitting search for source: {source}")
            source_config = getattr(settings, 'ACADEMIC_APIS', {}).get(source.upper(), {})
            if not source_config.get('ENABLED', source in ['arxiv', 'semantic_scholar']):
                search_stats[source] = {
                    'error': 'Source not enabled in configuration',
                    'count': 0,
                    'status': 'disabled'
                }
                continue
            future = executor.submit(search_functions[source], query, max_results_per_source)
            future_to_source[future] = source
        for future in as_completed(future_to_source, timeout=45):
            source = future_to_source[future]
            try:
                start_time = time.time()
                papers = future.result(timeout=20)
                search_time = round(time.time() - start_time, 2)
                valid_papers = [p for p in papers if p.get('title') and len(p.get('title', '')) > 5]
                all_papers.extend(valid_papers)
                search_stats[source] = {
                    'count': len(valid_papers),
                    'status': 'success',
                    'search_time': search_time,
                    'total_found': len(papers)
                }
                logger.info(f"Successfully retrieved {len(valid_papers)} papers from {source} in {search_time}s")
            except Exception as e:
                error_msg = str(e)
                if 'timeout' in error_msg.lower():
                    error_msg = 'Search timeout - try again later'
                elif 'api' in error_msg.lower():
                    error_msg = 'API error - check configuration'
                search_stats[source] = {
                    'error': error_msg,
                    'count': 0,
                    'status': 'error'
                }
                logger.error(f"Error searching {source}: {e}")
    unique_papers = deduplicate_papers(all_papers)
    unique_papers = sort_papers_by_relevance(unique_papers, query)
    return unique_papers, search_stats

def search_arxiv_papers(query, max_results=20):
    base_url = getattr(settings, 'ACADEMIC_APIS', {}).get('ARXIV', {}).get('BASE_URL', 'http://export.arxiv.org/api/query')
    formatted_query = format_arxiv_query(query)
    params = {
        'search_query': formatted_query,
        'start': 0,
        'max_results': max_results,
        'sortBy': 'relevance',
        'sortOrder': 'descending'
    }
    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            logger.error(f"XML parsing error for arXiv: {e}")
            return []
        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
        papers = []
        for entry in root.findall('atom:entry', namespaces):
            paper = extract_arxiv_paper_info(entry, namespaces)
            if paper:
                paper['source'] = 'arXiv'
                paper['source_icon'] = 'fas fa-archive'
                paper['relevance_score'] = calculate_relevance_score(paper, query)
                papers.append(paper)
        return papers
    except requests.RequestException as e:
        logger.error(f"Network error fetching arXiv papers: {e}")
        raise Exception("Network error accessing arXiv")
    except Exception as e:
        logger.error(f"Unexpected error fetching arXiv papers: {e}")
        raise Exception("Error processing arXiv results")

def search_semantic_scholar(query, max_results=20):
    print("DEBUG: search_semantic_scholar called")
    base_url = f"{getattr(settings, 'ACADEMIC_APIS', {}).get('SEMANTIC_SCHOLAR', {}).get('BASE_URL', 'https://api.semanticscholar.org/graph/v1')}/paper/search"
    headers = {'User-Agent': 'Research-Hub/1.0'}
    api_key = getattr(settings, 'ACADEMIC_APIS', {}).get('SEMANTIC_SCHOLAR', {}).get('API_KEY')
    if api_key:
        headers['x-api-key'] = api_key
    params = {
        'query': query,
        'limit': max_results,
        'fields': 'title,authors,abstract,url,year,citationCount,venue,externalIds,openAccessPdf,publicationTypes,fieldsOfStudy'
    }
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        papers = []
        for item in data.get('data', []):
            if not item.get('title') or len(item.get('title', '')) < 5:
                continue
            paper = {
                'title': clean_text(item.get('title', 'No title')),
                'authors': [author.get('name', '') for author in item.get('authors', [])],
                'summary': clean_text(item.get('abstract', 'No abstract available')[:500]),
                'link': item.get('url', ''),
                'pdf_link': '',
                'published': format_publication_date(item.get('year')),
                'category': item.get('venue', 'General Research'),
                'source': 'Semantic Scholar',
                'source_icon': 'fas fa-brain',
                'citation_count': item.get('citationCount', 0),
                'categories': item.get('fieldsOfStudy', []),
                'publication_types': item.get('publicationTypes', [])
            }
            if item.get('openAccessPdf') and item['openAccessPdf'].get('url'):
                paper['pdf_link'] = item['openAccessPdf']['url']
            elif item.get('externalIds', {}).get('ArXiv'):
                paper['pdf_link'] = f"https://arxiv.org/pdf/{item['externalIds']['ArXiv']}.pdf"
            paper['relevance_score'] = calculate_relevance_score(paper, query)
            papers.append(paper)
        return papers
    except requests.RequestException as e:
        logger.error(f"Network error fetching Semantic Scholar papers: {e}")
        raise Exception("Network error accessing Semantic Scholar")
    except Exception as e:
        logger.error(f"Error fetching Semantic Scholar papers: {e}")
        raise Exception("Error processing Semantic Scholar results")

def search_google_scholar(query, max_results=10):
    api_key = getattr(settings, 'ACADEMIC_APIS', {}).get('GOOGLE_SCHOLAR', {}).get('API_KEY')
    search_engine_id = getattr(settings, 'ACADEMIC_APIS', {}).get('GOOGLE_SCHOLAR', {}).get('SEARCH_ENGINE_ID')
    if not api_key or not search_engine_id:
        raise Exception("Google Scholar API credentials not configured")
    base_url = getattr(settings, 'ACADEMIC_APIS', {}).get('GOOGLE_SCHOLAR', {}).get('BASE_URL', 'https://www.googleapis.com/customsearch/v1')
    academic_query = f'"{query}" (filetype:pdf OR site:scholar.google.com OR site:arxiv.org OR site:semanticscholar.org)'
    params = {
        'key': api_key,
        'cx': search_engine_id,
        'q': academic_query,
        'num': min(max_results, 10),
        'searchType': 'web',
        'lr': 'lang_en',
        'safe': 'active'
    }
    try:
        response = requests.get(base_url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        papers = []
        for item in data.get('items', []):
            title = clean_text(item.get('title', 'No title'))
            snippet = item.get('snippet', '')
            paper = {
                'title': title,
                'authors': extract_authors_from_snippet(snippet),
                'summary': clean_text(snippet)[:400],
                'link': item.get('link', ''),
                'pdf_link': item.get('link', '') if 'pdf' in item.get('link', '').lower() else '',
                'published': extract_year_from_snippet(snippet),
                'category': extract_field_from_snippet(snippet),
                'source': 'Google Scholar',
                'source_icon': 'fab fa-google',
                'categories': [],
                'relevance_score': calculate_relevance_score({'title': title, 'summary': snippet}, query)
            }
            papers.append(paper)
        return papers
    except Exception as e:
        logger.error(f"Error fetching Google Scholar papers: {e}")
        raise Exception("Error accessing Google Scholar")

def search_ieee_xplore(query, max_results=20):
    api_key = getattr(settings, 'ACADEMIC_APIS', {}).get('IEEE_XPLORE', {}).get('API_KEY')
    if not api_key:
        raise Exception("IEEE Xplore API key not configured")
    base_url = getattr(settings, 'ACADEMIC_APIS', {}).get('IEEE_XPLORE', {}).get('BASE_URL', 'https://ieeexploreapi.ieee.org/api/v1/search/articles')
    params = {
        'apikey': api_key,
        'querytext': query,
        'max_records': max_results,
        'start_record': 1,
        'sort_field': 'relevance',
        'sort_order': 'desc',
        'format': 'json'
    }
    try:
        response = requests.get(base_url, params=params, timeout=25)
        response.raise_for_status()
        data = response.json()
        papers = []
        for item in data.get('articles', []):
            if not item.get('title'):
                continue
            paper = {
                'title': clean_text(item.get('title', 'No title')),
                'authors': extract_ieee_authors(item.get('authors', {})),
                'summary': clean_text(item.get('abstract', 'No abstract available')[:500]),
                'link': item.get('html_url', ''),
                'pdf_link': item.get('pdf_url', ''),
                'published': format_publication_date(item.get('publication_year')),
                'category': clean_text(item.get('publication_title', 'Engineering')),
                'source': 'IEEE Xplore',
                'source_icon': 'fas fa-microchip',
                'categories': [],
                'citation_count': item.get('citing_paper_count', 0)
            }
            paper['relevance_score'] = calculate_relevance_score(paper, query)
            papers.append(paper)
        return papers
    except Exception as e:
        logger.error(f"Error fetching IEEE Xplore papers: {e}")
        raise Exception("Error accessing IEEE Xplore")

def extract_ieee_authors(authors_data):
    if not authors_data:
        return []
    authors = []
    if isinstance(authors_data, dict) and 'authors' in authors_data:
        for author in authors_data['authors']:
            if isinstance(author, dict):
                name = author.get('full_name', '')
                if name:
                    authors.append(name)
    return authors

def search_springer(query, max_results=20):
    print("DEBUG: search_springer called")
    api_key = getattr(settings, 'ACADEMIC_APIS', {}).get('SPRINGER', {}).get('API_KEY')
    if not api_key:
        raise Exception("Springer API key not configured")
    base_url = getattr(settings, 'ACADEMIC_APIS', {}).get('SPRINGER', {}).get('BASE_URL', 'http://api.springernature.com/meta/v2/json')
    params = {
        'q': query,
        'api_key': api_key,
        'p': max_results,
        's': 1
    }
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        papers = []
        if 'records' in data:
            for record in data['records']:
                paper = {
                    'title': record.get('title', 'No title'),
                    'authors': [author.get('creator', '') for author in record.get('creators', [])],
                    'summary': record.get('abstract', ''),
                    'link': record.get('url', [{}])[0].get('value', '') if record.get('url') else '',
                    'published': record.get('publicationDate', ''),
                    'category': record.get('publicationName', ''),
                    'source': 'Springer Nature',
                    'source_icon': 'fas fa-book-open',
                    'citation_count': 0,
                    'pdf_link': '',
                }
                papers.append(paper)
        return papers
    except Exception as e:
        raise Exception(f"Error fetching from Springer API: {str(e)}")

def search_elsevier(query, max_results=20):
    api_key = getattr(settings, 'ACADEMIC_APIS', {}).get('ELSEVIER', {}).get('API_KEY')
    if not api_key:
        raise Exception("Elsevier API key not configured")
    base_url = getattr(settings, 'ACADEMIC_APIS', {}).get('ELSEVIER', {}).get('BASE_URL', 'https://api.elsevier.com/content/search/scopus')
    headers = {
        'X-ELS-APIKey': api_key,
        'Accept': 'application/json'
    }
    params = {
        'query': f'TITLE-ABS-KEY({query})',
        'count': min(max_results, 25),
        'start': 0,
        'sort': 'relevancy',
        'field': 'dc:title,dc:creator,prism:publicationName,prism:coverDate,dc:description,prism:doi,citedby-count,prism:issn,prism:isbn,dc:identifier,affiliation,author-count,openaccess,fund-sponsor'
    }
    try:
        response = requests.get(base_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        papers = []
        for entry in data['search-results']['entry']:
            if entry.get('error'):
                continue

            # Robust author extraction
            # Robust author extraction with fallback
            author_str = 'Unknown Author'
            if isinstance(entry.get('author'), list):
                author_str = ', '.join(
                    a.get('authname', '') for a in entry['author'] if isinstance(a, dict)
                )
            elif 'dc:creator' in entry:
                author_str = entry['dc:creator']

            scopus_link = ''
            for l in entry.get('link', []):
                if l.get('@ref') == 'scopus':
                    scopus_link = l.get('@href')
                    break

            paper = {
                'title': entry.get('dc:title', 'No title'),
                'author': author_str,
                'summary': entry.get('dc:description', ''),
                'link': scopus_link or '',
                'published': entry.get('prism:coverDate', ''),
                'category': entry.get('prism:publicationName', ''),
                'source': 'Elsevier/Scopus',
                'source_icon': 'fas fa-graduation-cap',
                'citation_count': int(entry.get('citedby-count', 0)),
                'pdf_link': '',
            }
            papers.append(paper)
        return papers
    except Exception as e:
        raise Exception(f"Error fetching from Elsevier API: {str(e)}")

# --- Helper functions below ---

def extract_arxiv_paper_info(entry, namespaces):
    try:
        paper = {}
        title_elem = entry.find('atom:title', namespaces)
        paper['title'] = title_elem.text.strip().replace('\n', ' ') if title_elem is not None else 'No title'
        authors = []
        for author in entry.findall('atom:author', namespaces):
            name_elem = author.find('atom:name', namespaces)
            if name_elem is not None:
                authors.append(name_elem.text.strip())
        paper['authors'] = authors
        summary_elem = entry.find('atom:summary', namespaces)
        paper['summary'] = summary_elem.text.strip().replace('\n', ' ') if summary_elem is not None else ''
        id_elem = entry.find('atom:id', namespaces)
        if id_elem is not None:
            arxiv_url = id_elem.text.strip()
            paper['link'] = arxiv_url
        doi_elem = entry.find('arxiv:doi', namespaces)
        paper['doi'] = doi_elem.text.strip() if doi_elem is not None else ''
        published_elem = entry.find('atom:published', namespaces)
        if published_elem is not None:
            paper['published'] = published_elem.text.strip()[:10]
        categories = []
        for category in entry.findall('atom:category', namespaces):
            term = category.get('term')
            if term:
                categories.append(term)
        paper['categories'] = categories
        paper['primary_category'] = categories[0] if categories else ''
        journal_elem = entry.find('arxiv:journal_ref', namespaces)
        paper['journal'] = journal_elem.text.strip() if journal_elem is not None else ''
        comment_elem = entry.find('arxiv:comment', namespaces)
        paper['comment'] = comment_elem.text.strip() if comment_elem is not None else ''
        links = []
        for link in entry.findall('atom:link', namespaces):
            link_info = {
                'href': link.get('href', ''),
                'rel': link.get('rel', ''),
                'type': link.get('type', ''),
                'title': link.get('title', '')
            }
            links.append(link_info)
        paper['links'] = links
        pdf_link = None
        for link in links:
            if link.get('type') == 'application/pdf' or 'pdf' in link.get('href', '').lower():
                pdf_link = link.get('href')
                break
        paper['pdf_link'] = pdf_link
        paper['source'] = 'arXiv'
        paper['source_icon'] = 'fas fa-archive'
        paper['citation_count'] = 0
        paper['open_access'] = True
        return paper
    except Exception as e:
        print(f"Error extracting ArXiv paper info: {str(e)}")
        return None

def calculate_relevance_score(paper, query):
    score = 0
    query_words = query.lower().split()
    title = paper.get('title', '').lower()
    title_matches = sum(1 for word in query_words if word in title)
    score += title_matches * 3
    abstract = paper.get('summary', '').lower()
    abstract_matches = sum(1 for word in query_words if word in abstract)
    score += abstract_matches * 2
    authors = ' '.join(paper.get('authors', [])).lower()
    author_matches = sum(1 for word in query_words if word in authors)
    score += author_matches * 1
    categories = ' '.join(paper.get('categories', []) + [paper.get('primary_category', '')]).lower()
    category_matches = sum(1 for word in query_words if word in categories)
    score += category_matches * 1.5
    journal = paper.get('journal', '').lower()
    journal_matches = sum(1 for word in query_words if word in journal)
    score += journal_matches * 1
    return score

def deduplicate_papers(papers):
    if not papers:
        return []
    seen_titles = {}
    unique_papers = []
    for paper in papers:
        title = paper.get('title', '')
        if not title or len(title) < 5:
            continue
        normalized_title = re.sub(r'[^\w\s]', '', title.lower())
        normalized_title = ' '.join(normalized_title.split())
        is_duplicate = False
        for existing_title in seen_titles.keys():
            similarity = calculate_title_similarity(normalized_title, existing_title)
            if similarity > 0.85:
                is_duplicate = True
                existing_paper = seen_titles[existing_title]
                if (paper.get('citation_count', 0) > existing_paper.get('citation_count', 0) or
                    len(paper.get('summary', '')) > len(existing_paper.get('summary', ''))):
                    unique_papers.remove(existing_paper)
                    seen_titles[normalized_title] = paper
                    unique_papers.append(paper)
                break
        if not is_duplicate:
            seen_titles[normalized_title] = paper
            unique_papers.append(paper)
    return unique_papers

def calculate_title_similarity(title1, title2):
    words1 = set(title1.split())
    words2 = set(title2.split())
    if not words1 or not words2:
        return 0
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union)

def sort_papers_by_relevance(papers, query):
    return sorted(papers, key=lambda x: x.get('relevance_score', 0), reverse=True)

def format_arxiv_query(query):
    if len(query.split()) == 1:
        return f'all:{query}'
    else:
        return f'all:"{query}"'

def format_publication_date(year):
    if not year:
        return "Unknown"
    try:
        if isinstance(year, int) and 1900 <= year <= datetime.now().year:
            return str(year)
        return str(year)
    except:
        return "Unknown"

def clean_text(text):
    if not text:
        return ""
    text = ' '.join(text.split())
    text = re.sub(r'[^\w\s.,;:!?()\-\'\"]+', '', text)
    if len(text) > 1000:
        text = text[:997] + "..."
    return text.strip()

def extract_authors_from_snippet(snippet):
    if not snippet:
        return []
    patterns = [
        r'by ([A-Z][a-z]+ [A-Z][a-z]+(?:, [A-Z][a-z]+ [A-Z][a-z]+)*)',
        r'([A-Z][a-z]+ [A-Z][a-z]+) - ',
        r'([A-Z][a-z]+ [A-Z][a-z]+(?:, [A-Z][a-z]+ [A-Z][a-z]+)*) \('
    ]
    for pattern in patterns:
        match = re.search(pattern, snippet)
        if match:
            authors_str = match.group(1)
            return [author.strip() for author in authors_str.split(',')[:3]]
    return []

def extract_year_from_snippet(snippet):
    if not snippet:
        return 'Unknown'
    patterns = [
        r'\b(20[0-2][0-9])\b',
        r'\b(19[8-9][0-9])\b',
        r'\((\d{4})\)',
        r'in (\d{4})',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, snippet)
        if matches:
            year = int(matches[0])
            if 1950 <= year <= datetime.now().year:
                return str(year)
    return 'Unknown'

def extract_field_from_snippet(snippet):
    fields = {
        'computer science': ['algorithm', 'software', 'programming', 'AI', 'machine learning'],
        'physics': ['quantum', 'particle', 'electromagnetic', 'thermodynamics'],
        'biology': ['DNA', 'protein', 'cell', 'genetics', 'evolution'],
        'medicine': ['patient', 'clinical', 'medical', 'health', 'disease'],
        'chemistry': ['molecular', 'chemical', 'reaction', 'synthesis'],
        'mathematics': ['theorem', 'proof', 'equation', 'mathematical']
    }
    snippet_lower = snippet.lower()
    for field, keywords in fields.items():
        if any(keyword in snippet_lower for keyword in keywords):
            return field.title()
    return 'General Research'

# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import BookmarkList, BookmarkedPaper

@login_required
def create_bookmark_list(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            BookmarkList.objects.create(user=request.user, name=name)
        return redirect('view_bookmark_lists')
    return render(request, 'create_bookmark_list.html')


@login_required
def view_bookmark_lists(request):
    lists = BookmarkList.objects.filter(user=request.user)
    return render(request, 'view_bookmark_lists.html', {'lists': lists})


@login_required
def add_bookmark(request, list_id):
    bookmark_list = get_object_or_404(BookmarkList, id=list_id, user=request.user)

    if request.method == 'POST':
        # These should be passed from the frontend
        title = request.POST.get('title')
        author = request.POST.get('author')
        link = request.POST.get('link')
        published = request.POST.get('published')
        category = request.POST.get('category')
        citation_count = request.POST.get('citation_count', 0)

        BookmarkedPaper.objects.create(
            bookmark_list=bookmark_list,
            title=title,
            author=author,
            link=link,
            published=published,
            category=category,
            citation_count=citation_count
        )
        return redirect('view_bookmark_lists')

    return render(request, 'add_bookmark.html', {'bookmark_list': bookmark_list})
