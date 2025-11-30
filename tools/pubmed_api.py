"""
PubMed/NCBI E-utilities API Integration for C.O.R.E.

Searches PubMed for genomics literature, clinical trials, and treatment evidence.
Uses NCBI E-utilities API for structured literature retrieval.

Author: Faith Ogundimu
"""

import json
import logging
import os
import ssl
from typing import List, Dict, Any, Optional
from Bio import Entrez

logger = logging.getLogger(__name__)

# SSL bypass for development (REMOVE IN PRODUCTION)
ssl._create_default_https_context = ssl._create_unverified_context

# Configure Entrez email (required by NCBI)
ENTREZ_EMAIL = os.getenv("ENTREZ_EMAIL", "your.email@example.com")
Entrez.email = ENTREZ_EMAIL


def search_pubmed_literature(
    query: str,
    max_results: int = 5,
    search_type: str = "general"   
) -> str:
    """
    Search PubMed for genomics and cancer treatment literature.
    
    Uses NCBI E-utilities to search PubMed and return structured results
    with titles, abstracts, authors, and PMIDs for citation.
    
    Args:
        query: Search query (e.g., "PIK3CA H1047R alpelisib breast cancer")
        max_results: Maximum number of papers to return (default: 10)
        search_type: Type of search - "general", "clinical_trial", "review"
    
    Returns:
        JSON string containing paper results or error message
        
    Example:
        >>> search_pubmed_literature(
        ...     "PIK3CA H1047R breast cancer treatment",
        ...     max_results=5
        ... )
    """
    
    try:
        # Enhance query based on search type
        enhanced_query = _enhance_query(query, search_type)
        
        logger.info(f"Searching PubMed: {enhanced_query}")
        
        # Step 1: Search for PMIDs
        search_handle = Entrez.esearch(
            db="pubmed",
            term=enhanced_query,
            retmax=max_results,
            sort="relevance",
            usehistory="y"
        )
        search_results = Entrez.read(search_handle)
        search_handle.close()
        
        pmid_list = search_results.get("IdList", [])
        
        if not pmid_list:
            return json.dumps({
                "papers": [],
                "message": f"No results found for query: {query}",
                "query": enhanced_query,
                "total_found": 0
            })
        
        logger.info(f"Found {len(pmid_list)} papers")
        
        # Step 2: Fetch full details for PMIDs
        fetch_handle = Entrez.efetch(
            db="pubmed",
            id=",".join(pmid_list),
            retmode="xml"
        )
        fetch_results = Entrez.read(fetch_handle)
        fetch_handle.close()
        
        # Step 3: Parse and structure results
        papers = []
        
        for article in fetch_results.get("PubmedArticle", []):
            try:
                paper_info = _parse_pubmed_article(article)
                papers.append(paper_info)
            except Exception as e:
                logger.warning(f"Error parsing article: {e}")
                continue
        
        result = {
            "query": query,
            "enhanced_query": enhanced_query,
            "total_found": len(papers),
            "papers": papers,
            "search_type": search_type
        }
        
        logger.info(f"Successfully parsed {len(papers)} papers")
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_msg = f"PubMed API error: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "error": error_msg,
            "query": query,
            "papers": []
        })


def _enhance_query(query: str, search_type: str) -> str:
    """
    Enhance query with MeSH terms and filters based on search type.
    
    Args:
        query: Base query string
        search_type: Type of search to optimize for
    
    Returns:
        Enhanced query string with PubMed filters
    """
    base_query = query
    
    # Add human filter
    if "humans[MeSH]" not in base_query.lower():
        base_query = f"{base_query} AND humans[MeSH]"
    
    # Add type-specific filters
    if search_type == "clinical_trial":
        base_query = f"{base_query} AND (Clinical Trial[ptyp] OR Clinical Trial, Phase II[ptyp] OR Clinical Trial, Phase III[ptyp])"
    elif search_type == "review":
        base_query = f"{base_query} AND (Review[ptyp] OR Meta-Analysis[ptyp] OR Systematic Review[ptyp])"
    
    return base_query


def _parse_pubmed_article(article: Dict) -> Dict[str, Any]:
    """
    Parse a PubMed article record into structured format.
    
    Args:
        article: Raw PubMed article record from Entrez
    
    Returns:
        Structured dictionary with paper information
    """
    medline = article.get("MedlineCitation", {})
    article_data = medline.get("Article", {})
    
    # Extract PMID
    pmid = str(medline.get("PMID", "Unknown"))
    
    # Extract title
    title = article_data.get("ArticleTitle", "No title available")
    
    # Extract abstract
    abstract_data = article_data.get("Abstract", {})
    abstract_texts = abstract_data.get("AbstractText", [])
    
    if isinstance(abstract_texts, list):
        abstract = " ".join([str(text) for text in abstract_texts])
    else:
        abstract = str(abstract_texts) if abstract_texts else "No abstract available"
    
    # Extract authors
    author_list = article_data.get("AuthorList", [])
    authors = []
    for author in author_list[:6]:  # Limit to first 6 authors
        last_name = author.get("LastName", "")
        initials = author.get("Initials", "")
        if last_name:
            authors.append(f"{last_name} {initials}".strip())
    
    author_string = ", ".join(authors)
    if len(author_list) > 6:
        author_string += ", et al."
    
    # Extract journal info
    journal_data = article_data.get("Journal", {})
    journal_title = journal_data.get("Title", "Unknown Journal")
    
    # Extract publication date
    pub_date = article_data.get("ArticleDate", [])
    year = "Unknown"
    if pub_date:
        year = pub_date[0].get("Year", "Unknown")
    else:
        # Fallback to journal issue date
        journal_issue = journal_data.get("JournalIssue", {})
        pub_date_obj = journal_issue.get("PubDate", {})
        year = pub_date_obj.get("Year", "Unknown")
    
    # Extract publication type
    pub_type_list = article_data.get("PublicationTypeList", [])
    pub_types = [str(pt) for pt in pub_type_list]
    
    # Determine if it's a clinical trial
    is_clinical_trial = any("Clinical Trial" in pt for pt in pub_types)
    is_review = any("Review" in pt for pt in pub_types)
    is_meta_analysis = any("Meta-Analysis" in pt for pt in pub_types)
    
    # Determine study type
    if is_meta_analysis:
        study_type = "Meta-Analysis"
    elif is_review:
        study_type = "Review"
    elif is_clinical_trial:
        study_type = "Clinical Trial"
    else:
        study_type = "Original Research"
    
    # Extract MeSH terms (for understanding topic focus)
    mesh_list = medline.get("MeshHeadingList", [])
    mesh_terms = []
    for mesh in mesh_list[:10]:  # Limit to top 10
        descriptor = mesh.get("DescriptorName", {})
        if hasattr(descriptor, 'attributes'):
            mesh_terms.append(str(descriptor))
    
    # Build paper info
    paper_info = {
        "pmid": pmid,
        "title": title.strip(),
        "authors": author_string,
        "journal": journal_title,
        "year": year,
        "abstract": abstract.strip()[:500] + "..." if len(abstract) > 500 else abstract.strip(),
        "full_abstract": abstract.strip(),  # Keep full version for agent analysis
        "study_type": study_type,
        "is_clinical_trial": is_clinical_trial,
        "is_review": is_review,
        "mesh_terms": mesh_terms[:5],  # Top 5 MeSH terms
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"
    }
    
    return paper_info


def search_mutation_evidence(gene: str, variant: str, cancer_type: str = "breast cancer") -> str:
    """
    Search for clinical evidence on a specific mutation.
    
    Optimized query for finding mutation-specific treatment evidence.
    
    Args:
        gene: Gene name (e.g., "PIK3CA")
        variant: Variant notation (e.g., "H1047R")
        cancer_type: Cancer type (default: "breast cancer")
    
    Returns:
        JSON string with paper results
    
    Example:
        >>> search_mutation_evidence("PIK3CA", "H1047R")
    """
    query = f"{gene} {variant} {cancer_type} treatment"
    return search_pubmed_literature(query, max_results=10, search_type="general")


def search_drug_efficacy(drug_name: str, mutation: str, cancer_type: str = "breast cancer") -> str:
    """
    Search for drug efficacy evidence in specific mutation context.
    
    Args:
        drug_name: Drug name (e.g., "alpelisib", "trastuzumab")
        mutation: Mutation or gene (e.g., "PIK3CA mutation")
        cancer_type: Cancer type (default: "breast cancer")
    
    Returns:
        JSON string with paper results
    
    Example:
        >>> search_drug_efficacy("alpelisib", "PIK3CA mutation")
    """
    query = f"{drug_name} {mutation} {cancer_type}"
    return search_pubmed_literature(query, max_results=10, search_type="clinical_trial")


def search_landmark_trial(trial_name: str) -> str:
    """
    Search for a specific landmark clinical trial by name.
    
    Useful for finding key papers like SOLAR-1, CLEOPATRA, etc.
    
    Args:
        trial_name: Trial acronym or name (e.g., "SOLAR-1", "BYLieve")
    
    Returns:
        JSON string with paper results
    
    Example:
        >>> search_landmark_trial("SOLAR-1")
    """
    query = f"{trial_name} breast cancer"
    return search_pubmed_literature(query, max_results=5, search_type="clinical_trial")


def search_resistance_mechanisms(gene: str, drug: str, cancer_type: str = "breast cancer") -> str:
    """
    Search for resistance mechanisms to specific therapies.
    
    Args:
        gene: Gene involved in resistance (e.g., "PIK3CA", "ESR1")
        drug: Drug name (e.g., "endocrine therapy", "alpelisib")
        cancer_type: Cancer type (default: "breast cancer")
    
    Returns:
        JSON string with paper results
    
    Example:
        >>> search_resistance_mechanisms("PIK3CA", "endocrine therapy")
    """
    query = f"{gene} {drug} resistance {cancer_type}"
    return search_pubmed_literature(query, max_results=8, search_type="general")


def search_biomarker_prevalence(gene: str, variant: str, cancer_type: str = "breast cancer") -> str:
    """
    Search for prevalence data on specific biomarkers.
    
    Args:
        gene: Gene name
        variant: Variant notation
        cancer_type: Cancer type
    
    Returns:
        JSON string with paper results
    
    Example:
        >>> search_biomarker_prevalence("PIK3CA", "H1047R", "breast cancer")
    """
    query = f"{gene} {variant} prevalence frequency {cancer_type}"
    return search_pubmed_literature(query, max_results=8, search_type="general")


# ============= Testing =============

if __name__ == "__main__":
    """Test the PubMed API with various query types."""
    
    print("="*80)
    print("Testing PubMed API for C.O.R.E.")
    print("="*80)
    
    # Check if ENTREZ_EMAIL is set
    if ENTREZ_EMAIL == "your.email@example.com":
        print("\n⚠️  WARNING: Set ENTREZ_EMAIL in your .env file")
        print("NCBI requires a valid email for API access")
        print("Add: ENTREZ_EMAIL=your.email@example.com\n")
    
    # Test 1: Mutation evidence search
    print("\n🧬 Test 1: PIK3CA H1047R mutation evidence")
    print("-"*80)
    result1 = search_mutation_evidence("PIK3CA", "H1047R", "breast cancer")
    data1 = json.loads(result1)
    print(f"Found {data1.get('total_found', 0)} papers")
    if data1.get('papers'):
        first_paper = data1['papers'][0]
        print(f"Top result: {first_paper['title'][:80]}...")
        print(f"PMID: {first_paper['pmid']} | {first_paper['journal']} ({first_paper['year']})")
        print(f"Study type: {first_paper['study_type']}")
    
    # Test 2: Drug efficacy search
    print("\n💊 Test 2: Alpelisib efficacy in PIK3CA-mutant BC")
    print("-"*80)
    result2 = search_drug_efficacy("alpelisib", "PIK3CA mutation", "breast cancer")
    data2 = json.loads(result2)
    print(f"Found {data2.get('total_found', 0)} papers")
    if data2.get('papers'):
        first_paper = data2['papers'][0]
        print(f"Top result: {first_paper['title'][:80]}...")
        print(f"PMID: {first_paper['pmid']}")
    
    # Test 3: Landmark trial search
    print("\n🏆 Test 3: SOLAR-1 trial papers")
    print("-"*80)
    result3 = search_landmark_trial("SOLAR-1")
    data3 = json.loads(result3)
    print(f"Found {data3.get('total_found', 0)} papers")
    if data3.get('papers'):
        for i, paper in enumerate(data3['papers'][:3], 1):
            print(f"{i}. {paper['title'][:80]}...")
            print(f"   PMID: {paper['pmid']} | {paper['year']}")
    
    # Test 4: Resistance mechanism search
    print("\n⚠️  Test 4: PIK3CA and endocrine resistance")
    print("-"*80)
    result4 = search_resistance_mechanisms("PIK3CA", "endocrine therapy")
    data4 = json.loads(result4)
    print(f"Found {data4.get('total_found', 0)} papers")
    
    # Test 5: General literature search
    print("\n📚 Test 5: General search - 'PIK3CA breast cancer targeted therapy'")
    print("-"*80)
    result5 = search_pubmed_literature("PIK3CA breast cancer targeted therapy", max_results=5)
    data5 = json.loads(result5)
    print(f"Found {data5.get('total_found', 0)} papers")
    if data5.get('papers'):
        print("\nMeSH terms from top paper:", ", ".join(data5['papers'][0].get('mesh_terms', [])))
    
    print("\n" + "="*80)
    print("✅ PubMed API testing complete!")
    print("="*80)
    
    # Display sample paper structure
    if data1.get('papers'):
        print("\n📄 Sample Paper Structure:")
        print(json.dumps(data1['papers'][0], indent=2))