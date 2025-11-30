"""
ClinicalTrials.gov API Integration for C.O.R.E.

Searches for clinical trials matching genetic mutations and cancer types.
Adapted from previous synthetic lethality project for MDT case preparation.

Author: Faith Ogundimu
"""

import json
import logging
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


def search_clinical_trials(
    genes: str = "",
    mutation: str = "",
    cancer_type: str = "breast cancer",
    max_results: int = 10,
    phase: List[str] = None,    
    status: List[str] = None   
) -> str:
    """
    Search ClinicalTrials.gov for trials matching genetic criteria.
    
    This function searches the ClinicalTrials.gov API v2 for trials that match
    specific genetic biomarkers, mutations, and cancer types. Designed for
    genomic intelligence analysis in breast cancer MDT preparation.
    
    Args:
        genes: List of gene names (e.g., ["PIK3CA", "TP53"])
        mutation: Specific mutation (e.g., "H1047R", "R273H")
        cancer_type: Cancer type to search (default: "breast cancer")
        max_results: Maximum number of trials to return (default: 10)
        phase: Filter by phase (e.g., ["PHASE2", "PHASE3"])
        status: Filter by status (e.g., ["RECRUITING", "ACTIVE_NOT_RECRUITING"])
    
    Returns:
        JSON string containing trial results or error message
        
    Example:
        >>> search_clinical_trials(
        ...     genes=["PIK3CA"],
        ...     mutation="H1047R",
        ...     cancer_type="breast cancer",
        ...     status=["RECRUITING"]
        ... )
    """
    
    # Base URL for ClinicalTrials.gov API v2
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    
    try:
        # Build search query
        query_parts = []
        
        # Add gene-specific terms
        if genes:
            gene_query = " OR ".join([f"{gene} mutation" for gene in genes])
            query_parts.append(f"({gene_query})")
        
        # Add specific mutation if provided
        if mutation:
            query_parts.append(mutation)
        
        # Add cancer type
        query_parts.append(cancer_type)
        
        # Combine query parts
        search_query = " AND ".join(query_parts)
        
        # Build query parameters
        params = {
            "query.term": search_query,
            "pageSize": max_results,
            "format": "json"
        }
        
        # Add phase filter if specified
        if phase:
            # API v2 uses query.phase parameter
            params["filter.overallStatus"] = ",".join(phase)
        
        # Add status filter if specified
        if status:
            params["filter.overallStatus"] = ",".join(status)
        
        logger.info(f"Searching ClinicalTrials.gov: {search_query}")
        logger.debug(f"API parameters: {params}")
        
        # Make API request
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract relevant trial information
        trials = []
        studies = data.get("studies", [])
        
        if not studies:
            return json.dumps({
                "trials": [],
                "message": f"No trials found for query: {search_query}",
                "query": search_query
            })
        
        for study in studies:
            protocol = study.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            design_module = protocol.get("designModule", {})
            eligibility = protocol.get("eligibilityModule", {})
            contacts = protocol.get("contactsLocationsModule", {})
            
            # Extract key information
            trial_info = {
                "nct_id": identification.get("nctId", "Unknown"),
                "title": identification.get("officialTitle", identification.get("briefTitle", "No title")),
                "phase": ", ".join(design_module.get("phases", ["Not specified"])),
                "status": status_module.get("overallStatus", "Unknown"),
                "brief_summary": protocol.get("descriptionModule", {}).get("briefSummary", "No summary"),
                "conditions": protocol.get("conditionsModule", {}).get("conditions", []),
                "interventions": [
                    {
                        "type": interv.get("type", "Unknown"),
                        "name": interv.get("name", "Unknown")
                    }
                    for interv in protocol.get("armsInterventionsModule", {}).get("interventions", [])
                ],
                "eligibility_criteria": eligibility.get("eligibilityCriteria", "Not specified"),
                "sex": eligibility.get("sex", "ALL"),
                "minimum_age": eligibility.get("minimumAge", "Not specified"),
                "maximum_age": eligibility.get("maximumAge", "Not specified"),
                "enrollment": protocol.get("designModule", {}).get("enrollmentInfo", {}).get("count", "Not specified"),
                "sponsor": identification.get("organization", {}).get("fullName", "Unknown"),
                "locations": contacts.get("locations", []),
                "url": f"https://clinicaltrials.gov/study/{identification.get('nctId', '')}"
            }
            
            trials.append(trial_info)
        
        result = {
            "query": search_query,
            "total_found": len(trials),
            "trials": trials,
            "search_parameters": {
                "genes": genes,
                "mutation": mutation,
                "cancer_type": cancer_type,
                "phase": phase,
                "status": status
            }
        }
        
        logger.info(f"Found {len(trials)} trials for query: {search_query}")
        return json.dumps(result, indent=2)
    
    except requests.exceptions.RequestException as e:
        error_msg = f"ClinicalTrials.gov API request failed: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "error": error_msg,
            "query": search_query if 'search_query' in locals() else "Query not formed",
            "trials": []
        })
    
    except Exception as e:
        error_msg = f"Error searching clinical trials: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "error": error_msg,
            "trials": []
        })


def search_trials_by_mutation(gene: str, variant: str, cancer_type: str = "breast cancer") -> str:
    """
    Convenience function to search trials by specific mutation.
    
    Args:
        gene: Gene name (e.g., "PIK3CA")
        variant: Variant notation (e.g., "H1047R")
        cancer_type: Cancer type (default: "breast cancer")
    
    Returns:
        JSON string with trial results
    
    Example:
        >>> search_trials_by_mutation("PIK3CA", "H1047R")
    """
    return search_clinical_trials(
        genes=[gene],
        mutation=variant,
        cancer_type=cancer_type,
        status=["RECRUITING", "ACTIVE_NOT_RECRUITING"],
        phase=["PHASE2", "PHASE3"]
    )


def search_trials_by_pathway(pathway: str, cancer_type: str = "breast cancer") -> str:
    """
    Search trials targeting a specific biological pathway.
    
    Useful for finding trials when no specific mutation is detected but
    pathway involvement is known (e.g., PI3K pathway, DNA repair).
    
    Args:
        pathway: Pathway name (e.g., "PI3K inhibitor", "PARP inhibitor")
        cancer_type: Cancer type (default: "breast cancer")
    
    Returns:
        JSON string with trial results
    
    Example:
        >>> search_trials_by_pathway("PI3K inhibitor")
    """
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    
    try:
        search_query = f"{pathway} AND {cancer_type}"
        
        params = {
            "query.term": search_query,
            "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING",
            "pageSize": 10,
            "format": "json"
        }
        
        logger.info(f"Searching pathway-based trials: {search_query}")
        
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        studies = data.get("studies", [])
        
        trials = []
        for study in studies:
            protocol = study.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            
            trial_info = {
                "nct_id": identification.get("nctId", "Unknown"),
                "title": identification.get("officialTitle", identification.get("briefTitle", "No title")),
                "phase": ", ".join(protocol.get("designModule", {}).get("phases", ["Not specified"])),
                "status": protocol.get("statusModule", {}).get("overallStatus", "Unknown"),
                "url": f"https://clinicaltrials.gov/study/{identification.get('nctId', '')}"
            }
            trials.append(trial_info)
        
        result = {
            "query": search_query,
            "total_found": len(trials),
            "trials": trials
        }
        
        logger.info(f"Found {len(trials)} pathway-based trials")
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_msg = f"Error searching pathway trials: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "trials": []})


# ============= Testing =============

if __name__ == "__main__":
    """Test the clinical trials API with PIK3CA mutation."""
    
    print("="*80)
    print("Testing ClinicalTrials.gov API for C.O.R.E.")
    print("="*80)
    
    # Test 1: Search for PIK3CA H1047R trials
    print("\n🧬 Test 1: PIK3CA H1047R mutation trials")
    print("-"*80)
    result1 = search_trials_by_mutation("PIK3CA", "H1047R", "breast cancer")
    data1 = json.loads(result1)
    print(f"Found {data1.get('total_found', 0)} trials")
    if data1.get('trials'):
        print(f"First trial: {data1['trials'][0]['nct_id']} - {data1['trials'][0]['title'][:80]}...")
    
    # Test 2: Search for PI3K inhibitor trials (pathway-based)
    print("\n🔬 Test 2: PI3K inhibitor pathway trials")
    print("-"*80)
    result2 = search_trials_by_pathway("PI3K inhibitor", "breast cancer")
    data2 = json.loads(result2)
    print(f"Found {data2.get('total_found', 0)} trials")
    if data2.get('trials'):
        print(f"First trial: {data2['trials'][0]['nct_id']} - {data2['trials'][0]['title'][:80]}...")
    
    # Test 3: Multi-gene search
    print("\n🧬 Test 3: Multiple genes (PIK3CA, TP53)")
    print("-"*80)
    result3 = search_clinical_trials(
        genes=["PIK3CA", "TP53"],
        cancer_type="breast cancer",
        status=["RECRUITING"]
    )
    data3 = json.loads(result3)
    print(f"Found {data3.get('total_found', 0)} trials")
    
    print("\n" + "="*80)
    print("✅ ClinicalTrials.gov API testing complete!")
    print("="*80)