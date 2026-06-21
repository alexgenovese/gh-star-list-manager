#!/usr/bin/env python3
"""
Script batch per spostare i repo dalle categorie esistenti alle sottocategorie Agent-Tools
basate su keywords e linguistiche coerenti.
"""

import json
from categorizer import move_repo
from config import STARS_FILE

def main():
    if not STARS_FILE.exists():
        print("❌ File stars.json non trovato.")
        return
    
    print("🚀 Avvio spostamento batch per Skills/Agent-Tools...")
    print("-" * 60)
    
    # Carica i dati
    with open(STARS_FILE) as f:
        data = json.load(f)
    
    repos = data["repos"]
    categorized = data["categorized"]
    
    # Sottocategorie target
    subcategories = {
        "Skills/Agent-Tools/RAG": [
            "onyx-dot-app/onyx",  # topics: rag, vector-search
            "dify",               # topics: rag
            "langgenius/dify",
            "firecrawl/firecrawl", # topics: RAG implicito in AI-crawler
        ],
        "Skills/Agent-Tools/LLM-Tuning": [
            "unslothai/unsloth",    # topics: fine-tuning, llm
            "axolotl-ai-cloud/axolotl", # topics: fine-tuning, llm
            "bghira/SimpleTuner",    # topics: fine-tuning
            "SimpleTuner",
        ],
        "Skills/Agent-Tools/CLI-Utility": [
            "tw93/Mole",            # topics: command-line
            "activepieces/activepieces", # topics: CLI implicito in nome repo
            "dagucloud/dagu",        # topics: CLI in toolkit
            "CopilotKit/CopilotKit",  # cli implicito
            "n8n-io/n8n",           # topics: cli
            "warpdotdev/warp",       # topic: terminal
            "earendil-works/pi",    # topics: CLI
            "sanity-io/agent-toolkit", # n/a
            "affaan-m/ECC",          # topics: developer-tools, productivity
            "goose",
        ],
        "Skills/Agent-Tools/AI-Infrastructure": [
            "coder/coder",           # Go + CLI + agentic
            "Comfy-Org/ComfyUI",    # Python ML infra
            "vladmandic/sdnext",     # AI generative infra
            "langflow-ai/langflow",   # agents + LLM
            "builderz-labs/mission-control", # agent orchestration
            "CopilotKit/CopilotKit",  # agent-native/infra
        ],
        "Skills/Agent-Tools/Docs-Templates": [
            "ixartz/SaaS-Boilerplate", # topics: template
            "SaaS-Boilerplate",
            "AFFiNE",
            "toeverything/AFFiNE",  # topics non includono template, ma è una knowledge-base con docs/notes
        ],
        "Skills/Agent-Tools/Synthetic-Data": [
            # Placeholder per future espansione
        ]
    }
    
    total_moved = 0
    moved_list = []
    failed_moves = []
    
    for target_cat, repo_names in subcategories.items():
        print(f"\n📦 Lavorando su sottocategoria: {target_cat}")
        for repo_name in repo_names:
            ok, msg = move_repo(repo_name, target_cat, categorized)
            if ok:
                total_moved += 1
                moved_list.append((repo_name, target_cat))
                print(f"  ✅ {repo_name} → {target_cat}")
            else:
                failed_moves.append((repo_name, msg))
                print(f"  ⚠️ {repo_name}: {msg}")
    
    # Salva risultati
    with open(STARS_FILE, "w") as f:
        json.dump({"repos": repos, "categorized": categorized}, f, indent=2)
    
    print("\n" + "="*60)
    print("📋 RISULTATI SPOSTAMENTO BATCH")
    print("="*60)
    print(f"✅ Repository spostati con successo: {total_moved}")
    
    if moved_list:
        print("\n📋 Repository spostati:")
        for repo_name, new_cat in moved_list:
            print(f"  - {repo_name} → {new_cat}")
    
    if failed_moves:
        print("\n⚠️ Repository non spostati:")
        for repo_name, reason in failed_moves:
            print(f"  - {repo_name}: {reason}")
    
    # Riepilogo finale
    print("\n📊 Riepilogo sottocategorie Skills/Agent-Tools:")
    agent_cats = [
        "Skills/Agent-Tools/RAG",
        "Skills/Agent-Tools/LLM-Tuning",
        "Skills/Agent-Tools/CLI-Utility",
        "Skills/Agent-Tools/AI-Infrastructure",
        "Skills/Agent-Tools/Docs-Templates",
        "Skills/Agent-Tools/Synthetic-Data",
        "Skills/Agent-Tools"
    ]
    
    for cat in agent_cats:
        if cat in categorized:
            count = len(categorized[cat])
            print(f"  {cat}: {count} repo")

if __name__ == "__main__":
    main()