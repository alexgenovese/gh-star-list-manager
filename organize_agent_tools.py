#!/usr/bin/env python3
"""
Script per riorganizzare automaticamente le 418 stelle nella categoria Skills/Agent-Tools.
Crea sottocategorie verticali e sposta i repo in base alle keywords.
"""

import json
from pathlib import Path
from categorizer import reclassify_agent_tools_subcategories, get_all_categories
from config import STARS_FILE

def main():
    if not STARS_FILE.exists():
        print("❌ File stars.json non trovato. Assicurarsi che sia stato eseguito il caricamento iniziale.")
        return
    
    print("🚀 Avvio riorganizzazione automatica di Skills/Agent-Tools...")
    print("-" * 60)
    
    # Carica i dati
    with open(STARS_FILE) as f:
        data = json.load(f)
    
    repos = data["repos"]
    categorized = data["categorized"]
    
    original_count = sum(len(v) for v in categorized.values())
    print(f"📊 Repository totali da organizzare: {original_count}")
    
    if "Skills/Agent-Tools" not in categorized:
        print("⚠️ Categoria Skills/Agent-Tools non trovata. Creazione...")
        categorized["Skills/Agent-Tools"] = []
    
    # Esegui la riorganizzazione
    categorized = reclassify_agent_tools_subcategories(categorized)
    
    # Salva i risultati
    with open(STARS_FILE, "w") as f:
        json.dump({"repos": repos, "categorized": categorized}, f, indent=2)
    
    final_count = sum(len(v) for v in categorized.values())
    print(f"\n✅ Riorganizzazione completata!")
    print(f"📁 Dati salvati in: {STARS_FILE}")
    print(f"🔢 Repository totali: {final_count}")
    
    # Report finale dettagliato
    print("\n" + "="*60)
    print("📋 REPORT FINALE DI RIORGANIZZAZIONE")
    print("="*60)
    
    agent_tools_subcats = [
        "Skills/Agent-Tools/RAG",
        "Skills/Agent-Tools/LLM-Tuning",
        "Skills/Agent-Tools/Synthetic-Data",
        "Skills/Agent-Tools/AI-Infrastructure",
        "Skills/Agent-Tools/CLI-Utility",
        "Skills/Agent-Tools/Docs-Templates",
        "Skills/Agent-Tools"
    ]
    
    for subcat in agent_tools_subcats:
        if subcat in categorized:
            count = len(categorized[subcat])
            status_counts = {}
            for repo in categorized[subcat]:
                status = repo.get("status", "sconosciuta")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"\n📂 {subcat}")
            print(f"  📦 Repo: {count}")
            
            if status_counts:
                status_str = " ".join([f"{k}:{v}" for k, v in status_counts.items()])
                print(f"  📊 Status: {status_str}")
            
            # Mostra top 5 repo più popolari
            top_repos = sorted(categorized[subcat], key=lambda r: r.get("stargazers_count", 0), reverse=True)[:5]
            if top_repos:
                print(f"  🏆 Top repo:")
                for repo in top_repos:
                    stars = repo.get("stargazers_count", 0)
                    print(f"    - {repo['full_name']} ⭐{stars}")

if __name__ == "__main__":
    main()