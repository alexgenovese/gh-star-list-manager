#!/usr/bin/env python3
"""
Genera un report finale dettagliato della riorganizzazione di Agent-Tools.
"""

import json
from config import STARS_FILE

def main():
    if not STARS_FILE.exists():
        print("❌ File stars.json non trovato.")
        return
    
    print("📊 Generazione report finale Skills/Agent-Tools...")
    print("="*70)
    
    with open(STARS_FILE) as f:
        data = json.load(f)
    
    categorized = data["categorized"]
    
    # Sottocategorie da reportare
    agent_tools_cats = [
        "Skills/Agent-Tools/RAG",
        "Skills/Agent-Tools/LLM-Tuning",
        "Skills/Agent-Tools/Synthetic-Data",
        "Skills/Agent-Tools/AI-Infrastructure",
        "Skills/Agent-Tools/CLI-Utility",
        "Skills/Agent-Tools/Docs-Templates",
        "Skills/Agent-Tools"
    ]
    
    # Conteggio generale
    total_in_agent_tools = 0
    status_summary = {
        "attiva": 0, "stabile": 0, "abbandonata": 0,
        "archiviata": 0, "disabilitata": 0, "sconosciuta": 0
    }
    
    for repo in data["repos"]:
        if repo["category"].startswith("Skills/Agent-Tools"):
            total_in_agent_tools += 1
            status = repo.get("status", "sconosciuta")
            status_summary[status] += 1
    
    # Report per sottocategoria
    print(f"\n📈 STATISTICHE GENERALI Skills/Agent-Tools")
    print(f"  🔢 Repository totali nella gerarchia: {total_in_agent_tools}")
    print(f"  ⚡ {sum(status_summary.values())} repository categorizzate")
    print()
    
    status_icons = {
        "attiva": "✅", "stabile": "🟡", "abbandonata": "🚨",
        "archiviata": "🗄️", "disabilitata": "⚠️", "sconosciuta": "❓"
    }
    
    for status, count in status_summary.items():
        if count > 0:
            print(f"    {status_icons[status]} {status.capitalize()}: {count}")
    
    print("\n" + "="*70)
    print("📂 RIPARTIZIONE PER SOTTOCATEGORIA")
    print("="*70)
    
    # Mostra i repo per ogni sottocategoria
    for cat in agent_tools_cats:
        if cat in categorized and categorized[cat]:
            count = len(categorized[cat])
            status_dist = {}
            for repo in categorized[cat]:
                status = repo.get("status", "sconosciuta")
                status_dist[status] = status_dist.get(status, 0) + 1
            
            # Conta stelle
            total_stars = sum(repo.get("stargazers_count", 0) for repo in categorized[cat])
            
            print(f"\n📁 {cat}")
            print(f"  📦 Repository: {count}")
            print(f"  ⭐ Stelle totali: {total_stars}")
            
            # Status
            status_str = " ".join(
                f"{status_icons.get(s, '?')}{s}:{c}"
                for s, c in status_dist.items()
            )
            print(f"  📊 Status: {status_str}")
            
            # Top 5 repo per stelle
            top_repos = sorted(
                categorized[cat], 
                key=lambda r: r.get("stargazers_count", 0), 
                reverse=True
            )[:5]
            
            if top_repos:
                print(f"  🏆 Top repository:")
                for repo in top_repos:
                    stars = repo.get("stargazers_count", 0)
                    repo_status = repo.get("status", "sconosciuta")
                    status_icon = status_icons.get(repo_status, "❓")
                    lang = repo.get("language", "-")
                    print(f"    {status_icon} {repo['full_name']:40s} ⭐{stars:>6}  [{lang}]")
    
    # Summary finale
    print("\n" + "="*70)
    print("📋 CONTEGGIO FINALE")
    print("="*70)
    
    counters = {}
    for repo in data["repos"]:
        cat = repo["category"]
        if cat.startswith("Skills/Agent-Tools"):
            counters[cat] = counters.get(cat, 0) + 1
    
    # Ordina alfabeticamente
    for cat in sorted(counters.keys()):
        print(f"  {cat}: {counters[cat]} repo")
    
    total_final = sum(counters.values())
    
    print(f"\n🎉 OPERAZIONE COMPLETATA")
    print(f"  🔢 Repository totali rientranti in Skills/Agent-Tools: {total_final}")
    print(f"  ✅ Riorganizzazione automatica applicata!")
    print("="*70)

if __name__ == "__main__":
    main()