import os
import argparse
import json
import gzip
import csv
from src.filter import is_honeypot
from src.scoring import calculate_score
from src.reasoning import generate_reasoning

def parse_args():
    parser = argparse.ArgumentParser(description="Rank candidates for Senior AI Engineer JD.")
    parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl or candidates.jsonl.gz")
    parser.add_argument("--out", required=True, help="Path to output CSV file")
    return parser.parse_args()

def load_candidates(file_path):
    """
    Loads candidates from a JSONL file, supporting both gzipped and plain text formats.
    """
    print(f"Loading candidates from {file_path}...")
    candidates = []
    
    # Check if the file is gzipped
    if file_path.endswith(".gz"):
        open_func = gzip.open
        mode = "rt"
    else:
        open_func = open
        mode = "r"
        
    with open_func(file_path, mode, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            candidates.append(json.loads(line))
            if (i + 1) % 20000 == 0:
                print(f"  Loaded {i + 1} candidates...")
                
    print(f"Loaded {len(candidates)} total candidates.")
    return candidates

def main():
    args = parse_args()
    
    # Load data
    candidates = load_candidates(args.candidates)
    
    # Process candidates
    scored_candidates = []
    honeypot_count = 0
    
    print("Scoring and filtering candidates...")
    for cand in candidates:
        # 1. Filter out honeypots / impossible profiles
        if is_honeypot(cand):
            honeypot_count += 1
            continue
            
        # 2. Score candidate
        score = calculate_score(cand)
        scored_candidates.append((score, cand["candidate_id"], cand))
        
    print(f"Filtered out {honeypot_count} honeypots.")
    print(f"Scored {len(scored_candidates)} valid candidates.")
    
    # Sort by score descending, and break ties by candidate_id ascending
    # Python's sort is stable, so we sort by candidate_id ascending first, then score descending.
    scored_candidates.sort(key=lambda x: x[1]) # Sort by candidate_id ascending
    scored_candidates.sort(key=lambda x: x[0], reverse=True) # Sort by score descending
    
    # Select top 100 candidates
    top_100 = scored_candidates[:100]
    
    print(f"Writing top 100 candidates to {args.out}...")
    
    # Ensure output directory exists
    out_dir = os.path.dirname(args.out)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)
        
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        # Header row
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        
        for i, (score, cid, cand) in enumerate(top_100):
            rank = i + 1
            reasoning = generate_reasoning(cand, rank)
            writer.writerow([cid, rank, score, reasoning])
            
    print("Ranking successfully completed!")

if __name__ == "__main__":
    main()
