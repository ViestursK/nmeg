# import_topics.py
import json
import os
from db.database import Database

def import_topics():
    """Import Trustpilot topics into database"""
    db = Database()
    
    # Load topics JSON
    
    # Load topics JSON from project root
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    topics_file = os.path.join(root_dir, 'tp_topics.json')
    
    with open(topics_file, 'r', encoding='utf-8') as f:
        topics = json.load(f)
    
    print(f"📥 Importing {len(topics)} topics...")
    
    # Clear existing
    db.query("DELETE FROM topics;")
    
    count = 0
    for key, name in topics.items():
        # Generate search terms from key and name
        search_terms = set()
        
        # Add the key (underscore to space)
        search_terms.add(key.replace('_', ' '))
        
        # Add the name
        search_terms.add(name.lower())
        
        # Add singular/plural variations
        if name.endswith('s') and len(name) > 3:
            search_terms.add(name[:-1].lower())  # Remove 's'
        else:
            search_terms.add(name.lower() + 's')  # Add 's'
        
        # Convert to array
        search_array = list(search_terms)
        
        db.query("""
            INSERT INTO topics (topic_key, topic_name, search_terms)
            VALUES (%s, %s, %s)
            ON CONFLICT (topic_key) DO UPDATE SET
                topic_name = EXCLUDED.topic_name,
                search_terms = EXCLUDED.search_terms;
        """, (key, name, search_array))
        
        count += 1
    
    db.close()
    print(f"✅ Imported {count} topics")

if __name__ == "__main__":
    import_topics()