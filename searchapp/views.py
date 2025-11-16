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

from urllib.parse import urlparse, urlencode, parse_qs
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")

            # Handle redirect with preserved parameters
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                # Parse the URL and maintain all query parameters
                from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
                
                parsed_url = urlparse(next_url)
                query_params = parse_qs(parsed_url.query)
                
                # Convert back to proper format (parse_qs creates lists)
                clean_params = {}
                for key, value_list in query_params.items():
                    if value_list:
                        clean_params[key] = value_list[0]
                
                # Reconstruct URL with all parameters
                new_query = urlencode(clean_params)
                final_url = urlunparse((
                    parsed_url.scheme,
                    parsed_url.netloc,
                    parsed_url.path,
                    parsed_url.params,
                    new_query,
                    parsed_url.fragment
                ))
                
                return redirect(final_url)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    # Preserve 'next' from GET so it can be rendered in the form
    next_param = request.GET.get('next', '')

    return render(request, 'login.html', {
        'form': form,
        'next': next_param,
    })

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

def land(request):
    return render(request, 'landing.html')

def home(request):
    query = request.GET.get('query', '').strip()
    sources = request.GET.getlist('sources')
    bookmark_lists = BookmarkList.objects.filter(user=request.user) if request.user.is_authenticated else []

    if not sources:
        sources = ['arxiv']

    papers = []
    search_stats = {}
    keywords = []

    if query and len(query) < 2:
        messages.warning(request, 'Search query must be at least 2 characters long.')
        query = ''

    if query:
        try:
            papers, search_stats = search_multiple_sources(query, sources)
            total_papers = len(papers)
            if total_papers > 0:
                messages.success(request, f'Found {total_papers} papers from {len([s for s in search_stats.values() if s.get("count", 0) > 0])} sources.')
            else:
                messages.info(request, 'No papers found. Try different sources or queries.')

            # ✅ Store the query for autocomplete (unique)
            if len(query) >= 2:
                SearchQuery.objects.get_or_create(query=query)

            # ✅ Extract keywords from fetched paper titles
            keywords = extract_keywords_from_papers(papers)

        except Exception as e:
            print("Search error:", e)
            messages.error(request, 'An error occurred during search.')

    available_sources = get_available_sources()

    context = {
        'query': query,
        'papers': papers[:50],
        'selected_sources': sources,
        'available_sources': available_sources,
        'search_stats': search_stats,
        'total_results': len(papers),
        'search_performed': bool(query),
        'bookmark_lists': bookmark_lists,
        'suggested_keywords': keywords,
    }

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
    if getattr(settings, 'ACADEMIC_APIS', {}).get('PUBMED', {}).get('ENABLED', True):
        api_key = getattr(settings, 'ACADEMIC_APIS', {}).get('PUBMED', {}).get('API_KEY')
        sources.append({
            'id': 'pubmed',
            'name': 'PubMed',
            'icon': 'fas fa-notes-medical',
            'description': 'Biomedical and life sciences literature by NCBI',
            'free': True,
            'rate_limit': 300,  # E-utilities has generous rate limits with API key
            'quality': 'High',
            'fields': ['Medicine', 'Pharmacy', 'Biology', 'Healthcare'],
            'configured': True  # PubMed works without an API key too
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
        'google_scholar': search_google_scholar,
        'pubmed': search_pubmed,
        'springer': search_springer,
        'elsevier': search_elsevier
    }
    valid_sources = [s for s in sources if s in search_functions]
    if not valid_sources:
        return [], {'error': 'No valid sources selected'}
    with ThreadPoolExecutor(max_workers=min(len(valid_sources), 6)) as executor:
        future_to_source = {}
        for source in valid_sources:
            # print(f"DEBUG: Submitting search for source: {source}")
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


def search_google_scholar(query, max_results=10):
    api_key = getattr(settings, 'ACADEMIC_APIS', {}).get('GOOGLE_SCHOLAR', {}).get('API_KEY')
    base_url = getattr(settings, 'ACADEMIC_APIS', {}).get('GOOGLE_SCHOLAR', {}).get('BASE_URL', 'https://www.searchapi.io/api/v1/search')

    if not api_key:
        raise Exception("Google Scholar API key not configured")

    params = {
        'api_key': api_key,
        'engine': 'google_scholar',
        'q': query,
    }

    headers = {
        'User-Agent': 'Mozilla/5.0'
    }

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=20)
        print("Requested URL:", response.url)
        print("Status Code:", response.status_code)

        response.raise_for_status()
        data = response.json()

        # Optional: Print entire JSON response for debugging
        print("Response JSON:", json.dumps(data, indent=2))

        results = data.get('organic_results', [])
        if not results:
            print("⚠️ No organic_results found.")
            return []

        papers = []
        for item in results[:max_results]:
            try:
                title = clean_text(item.get('title', 'No title'))
                snippet = item.get('snippet', '')
                link = item.get('link', '')
                pdf_link = item.get('resource', {}).get('link', '') if item.get('resource', {}).get('format', '').lower() == 'pdf' else ''

                # Extract authors list if available
                authors = []
                for a in item.get('authors', []):
                    authors.append(a.get('name'))

                paper = {
                    'title': title,
                    'authors': authors,
                    'summary': clean_text(snippet)[:400],
                    'link': link,
                    'pdf_link': pdf_link,
                    'published': item.get('publication', '').split(",")[-1].strip(),  # crude year extraction
                    'category': '',
                    'source': 'Google Scholar',
                    'source_icon': 'fab fa-google',
                    'categories': [],
                    'relevance_score': calculate_relevance_score({'title': title, 'summary': snippet}, query)
                }
                print("✅ Added:", paper['title'])
                papers.append(paper)
            except Exception as e:
                print("❌ Error parsing item:", e)

        return papers

    except Exception as e:
        logger.error(f"Error fetching papers from SearchAPI.io: {e}")
        raise Exception("Error accessing Google Scholar API")

import xml.etree.ElementTree as ET

def search_pubmed(query, max_results=20):
    import requests
    from urllib.parse import urlencode

    esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    search_params = {
        'db': 'pubmed',
        'term': query,
        'retmode': 'json',
        'retmax': max_results
    }

    try:
        # Step 1: Search for PubMed IDs
        esearch_response = requests.get(esearch_url, params=search_params, timeout=10)
        esearch_response.raise_for_status()
        id_list = esearch_response.json().get('esearchresult', {}).get('idlist', [])
        if not id_list:
            return []

        # Step 2: Fetch details using efetch
        fetch_params = {
            'db': 'pubmed',
            'id': ','.join(id_list),
            'retmode': 'xml'
        }
        efetch_response = requests.get(efetch_url, params=fetch_params, timeout=15)
        efetch_response.raise_for_status()

        # Step 3: Parse XML
        root = ET.fromstring(efetch_response.content)
        papers = []
        for article in root.findall('.//PubmedArticle'):
            title = article.findtext('.//ArticleTitle', default='No Title')
            abstract = article.findtext('.//Abstract/AbstractText', default='No abstract available')
            pub_year = article.findtext('.//PubDate/Year', default='Unknown')
            journal = article.findtext('.//Journal/Title', default='Medical Research')
            article_id = article.findtext('.//ArticleId[@IdType="pubmed"]', default='')

            # Authors
            authors = []
            for author in article.findall('.//Author'):
                last = author.findtext('LastName')
                first = author.findtext('ForeName')
                if last and first:
                    authors.append(f"{first} {last}")

            paper = {
                'title': clean_text(title),
                'authors': authors,
                'summary': clean_text(abstract[:500]),
                'link': f"https://pubmed.ncbi.nlm.nih.gov/{article_id}/",
                'pdf_link': '',  # PubMed doesn’t host PDFs directly
                'published': format_publication_date(pub_year),
                'category': clean_text(journal),
                'source': 'PubMed',
                'source_icon': 'fas fa-notes-medical',
                'categories': [],
                'citation_count': 0,  # Not directly available from PubMed
                'relevance_score': calculate_relevance_score({'title': title, 'summary': abstract}, query)
            }
            papers.append(paper)

        return papers

    except Exception as e:
        logger.error(f"Error fetching PubMed papers: {e}")
        raise Exception("Error accessing PubMed")


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
        try:
            name = request.POST.get('name')
            if not name:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'List name is required'}, status=400)
                messages.error(request, 'List name is required')
                return redirect('view_bookmark_lists')
            
            bookmark_list = BookmarkList.objects.create(user=request.user, name=name)
            
            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'list_id': bookmark_list.id,
                    'list_name': bookmark_list.name
                })
            
            # Regular form submission
            messages.success(request, f'List "{name}" created successfully')
            return redirect('view_bookmark_lists')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
            messages.error(request, f'Error creating list: {str(e)}')
            return redirect('view_bookmark_lists')
    return render(request, 'create_bookmark_list.html')


@login_required
def view_bookmark_lists(request):
    lists = BookmarkList.objects.filter(user=request.user)
    return render(request, 'view_bookmark_lists.html', {'lists': lists})


@login_required
def add_bookmark(request, list_id=0):
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            author = request.POST.get('author')
            link = request.POST.get('link')
            published = request.POST.get('published')
            category = request.POST.get('category')
            citation_count = request.POST.get('citation_count', 0)

            # Handle list
            list_id = request.POST.get('list_id')
            new_list_name = request.POST.get('new_list_name')

            if new_list_name:
                bookmark_list = BookmarkList.objects.create(user=request.user, name=new_list_name)
            else:
                bookmark_list = get_object_or_404(BookmarkList, id=list_id, user=request.user)

            BookmarkedPaper.objects.create(
                bookmark_list=bookmark_list,
                title=title,
                author=author,
                link=link,
                published=published,
                category=category,
                citation_count=citation_count
            )

            return JsonResponse({'success': True, 'message': 'Bookmark saved successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def remove_bookmark(request, paper_id):
    if request.method == 'POST':
        try:
            paper = get_object_or_404(BookmarkedPaper, id=paper_id, bookmark_list__user=request.user)
            paper.delete()
            messages.success(request, 'Paper removed from bookmark list')
            return redirect('view_bookmark_lists')
        except Exception as e:
            messages.error(request, f'Error removing bookmark: {str(e)}')
            return redirect('view_bookmark_lists')
    return redirect('view_bookmark_lists')

# views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import SearchQuery, BookmarkList
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from rake_nltk import Rake

import nltk
nltk.download('stopwords')

# In-memory keyword cache (optional, could use Django cache later)
EXTRACTED_KEYWORDS = set()

def extract_keywords_from_papers(papers):
    global EXTRACTED_KEYWORDS
    r = Rake()
    all_titles = ' '.join(p['title'] for p in papers if 'title' in p)
    r.extract_keywords_from_text(all_titles)
    keywords = r.get_ranked_phrases()[:20]
    EXTRACTED_KEYWORDS.update(keywords)
    return list(EXTRACTED_KEYWORDS)

# views.py - Add this to your existing views.py file

import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import re

# Common academic keywords and research terms
ACADEMIC_KEYWORDS = [
    # Computer Science
    'machine learning', 'artificial intelligence', 'deep learning', 'neural networks',
    'natural language processing', 'computer vision', 'data mining', 'algorithms',
    'software engineering', 'cybersecurity', 'blockchain', 'cloud computing',
    'quantum computing', 'robotics', 'human-computer interaction', 'database systems',
    
    # Data Science & Analytics
    'data science', 'big data', 'data analysis', 'statistical analysis',
    'predictive modeling', 'classification', 'regression', 'clustering',
    'dimensionality reduction', 'feature selection', 'time series analysis',
    
    # Biology & Medicine
    'bioinformatics', 'genomics', 'proteomics', 'molecular biology',
    'neuroscience', 'cancer research', 'drug discovery', 'clinical trials',
    'epidemiology', 'public health', 'genetics', 'immunology',
    
    # Physics & Engineering
    'quantum mechanics', 'particle physics', 'materials science',
    'renewable energy', 'nanotechnology', 'biomedical engineering',
    'electrical engineering', 'mechanical engineering', 'civil engineering',
    
    # Social Sciences
    'psychology', 'sociology', 'economics', 'political science',
    'anthropology', 'education research', 'behavioral economics',
    'social network analysis', 'survey research', 'qualitative research',
    
    # Environmental Sciences
    'climate change', 'environmental science', 'sustainability',
    'ecology', 'conservation biology', 'renewable resources',
    'pollution control', 'green technology', 'carbon footprint',
    
    # Business & Management
    'business analytics', 'supply chain management', 'marketing research',
    'organizational behavior', 'strategic management', 'entrepreneurship',
    'financial modeling', 'risk management', 'operations research',
    
    # Research Methods
    'systematic review', 'meta-analysis', 'randomized controlled trial',
    'case study', 'experimental design', 'statistical significance',
    'correlation analysis', 'longitudinal study', 'cross-sectional study'
]

# Recent trending topics in research
TRENDING_TOPICS = [
    'covid-19', 'coronavirus', 'pandemic', 'vaccine development',
    'remote work', 'online learning', 'digital transformation',
    'climate change mitigation', 'sustainable development',
    'artificial general intelligence', 'large language models',
    'metaverse', 'web3', 'cryptocurrency', 'nft',
    'electric vehicles', 'battery technology', 'solar energy',
    'gene therapy', 'crispr', 'personalized medicine',
    'space exploration', 'mars colonization', 'satellite technology'
]

@require_http_methods(["GET"])
def autocomplete_suggestions(request):
    """
    Provide autocomplete suggestions for search queries
    """
    term = request.GET.get('term', '').strip().lower()
    
    if len(term) < 2:
        return JsonResponse({'suggestions': []})
    
    suggestions = []
    
    # Search in academic keywords
    matching_keywords = [
        keyword for keyword in ACADEMIC_KEYWORDS 
        if term in keyword.lower()
    ]
    
    # Search in trending topics
    matching_trends = [
        topic for topic in TRENDING_TOPICS 
        if term in topic.lower()
    ]
    
    # Combine and deduplicate
    all_matches = list(set(matching_keywords + matching_trends))
    
    # Sort by relevance (exact matches first, then contains)
    exact_matches = [match for match in all_matches if match.lower().startswith(term)]
    contains_matches = [match for match in all_matches if term in match.lower() and not match.lower().startswith(term)]
    
    # Combine and limit results
    suggestions = (exact_matches + contains_matches)[:10]
    
    # If we have previous searches (for logged-in users), include them
    if request.user.is_authenticated:
        # You can add logic here to fetch user's previous searches from database
        # For now, we'll just use the keyword suggestions
        pass
    
    return JsonResponse({
        'suggestions': suggestions,
        'total': len(suggestions)
    })

# Alternative implementation if you want to store and retrieve actual search history
# @login_required
# @require_http_methods(["GET"])
# def user_search_history(request):
#     """
#     Get user's search history for autocomplete
#     """
#     # This assumes you have a SearchHistory model
#     # You'll need to create this model and save searches
    
#     term = request.GET.get('term', '').strip().lower()
#     suggestions = []
    
#     if len(term) >= 2:
#         # Example: If you have a SearchHistory model
#         # from .models import SearchHistory
#         # 
#         # recent_searches = SearchHistory.objects.filter(
#         #     user=request.user,
#         #     query__icontains=term
#         # ).order_by('-created_at')[:5]
#         # 
#         # suggestions = [search.query for search in recent_searches]
#         pass
    
#     return JsonResponse({
#         'suggestions': suggestions,
#         'total': len(suggestions)
#     })

# Smart autocomplete that combines multiple sources
import re
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

ENGLISH_SIMPLE_RE = re.compile(r'^[A-Za-z0-9\s\-\_\:\,\.\(\)\'"&/]+$')  # allows common punctuation

@require_http_methods(["GET"])
def smart_autocomplete(request):
    """
    Advanced autocomplete that:
      - filters to simple English-looking suggestions
      - ranks exact prefix -> word-boundary -> contains -> fuzzy
      - returns up to max_results (defaults to 5)
    """
    term = request.GET.get('term', '').strip().lower()
    if len(term) < 2:
        return JsonResponse({'suggestions': [], 'total': 0})

    try:
        max_results = int(request.GET.get('limit', 5))
    except ValueError:
        max_results = 5

    def is_english_like(s: str) -> bool:
        # Simple heuristic: allow ASCII letters, numbers and common punctuation.
        # This will drop non-Latin scripts. If you require more accuracy, use a language detection library.
        return bool(ENGLISH_SIMPLE_RE.match(s))

    # collect from both sources
    pool = list(set(ACADEMIC_KEYWORDS + TRENDING_TOPICS))

    # filter English-like only
    pool = [p for p in pool if is_english_like(p)]

    # normalization helpers
    pool_lower_map = {p.lower(): p for p in pool}  # preserve original casing

    # exact prefix matches
    exact_matches = [orig for low, orig in pool_lower_map.items() if low.startswith(term)]
    # word-boundary matches (term at a word boundary, but not prefix)
    word_matches = [
        orig for low, orig in pool_lower_map.items()
        if re.search(r'\b' + re.escape(term), low) and not low.startswith(term)
    ]
    # contains matches (term anywhere)
    contains_matches = [
        orig for low, orig in pool_lower_map.items()
        if term in low and not low.startswith(term) and not re.search(r'\b' + re.escape(term), low)
    ]

    # simple fuzzy fallback for longer terms (very basic)
    fuzzy_matches = []
    if len(term) >= 3:
        for low, orig in pool_lower_map.items():
            # prevent duplicates and obvious misses
            if orig in exact_matches + word_matches + contains_matches:
                continue
            # simple character overlap ratio
            match_ratio = sum(1 for a, b in zip(term, low) if a == b) / max(len(term), len(low))
            if match_ratio > 0.6:
                fuzzy_matches.append(orig)

    # compose final prioritized list and limit
    ordered = []
    for src in (exact_matches, word_matches, contains_matches, fuzzy_matches):
        for s in src:
            if s not in ordered:
                ordered.append(s)
            if len(ordered) >= max_results:
                break
        if len(ordered) >= max_results:
            break

    # final formatting: keep original casing, optional title-case
    suggestions = ordered[:max_results]

    return JsonResponse({
        'suggestions': suggestions,
        'total': len(suggestions)
    })
