# ReFindr – Academic Paper Finder  

ReFindr is a Django-powered web application that helps students and researchers **search academic papers across multiple sources**, filter them, and curate personalized bookmark lists. The goal is to make paper discovery seamless and distraction-free.  

---

## Features  

- 🔎 **Multi-Source Search** – Fetch academic papers from various repositories.  
- 🧩 **Source Filtering** – Select and refine results by academic database.  
- 📑 **Bookmark Lists** – Save and organize papers into custom collections.  
- 🔐 **User Authentication** – Secure login for personalized experience.  
- ⚡ **Autocomplete Search** – Smart suggestions while typing queries.  
- 📱 **Responsive UI** – Tailwind CSS for a clean, mobile-first interface.  

---

## Tech Stack  

| Layer        | Technologies Used |
|--------------|------------------|
| **Frontend** | HTML5, Tailwind CSS, JavaScript |
| **Backend**  | Django (Python) |
| **Database** | PostgreSQL |
| **NLP Features** | Autocomplete suggestions, Auto-tagging, Extractive summarization | 

---

## Project Structure

```text
refindr-research/
├── refindr/          # Core Django project files
├── search/           # Search functionality: views, queries, autocomplete
├── bookmarks/        # Bookmark creation, listing, and management
├── users/            # Authentication, login, signup
├── static/           # Tailwind CSS, JS, and static assets
├── templates/        # HTML templates for frontend
├── requirements.txt  # Python dependencies
└── README.md
