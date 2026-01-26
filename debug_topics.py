from db import Database
import json

db = Database()

# Check AI summaries
print("Checking AI summaries table...")
summaries = db.query("SELECT * FROM ai_summaries;")

if summaries:
    for summary in summaries:
        print(f"\nCompany ID: {summary['company_id']}")
        print(f"Summary: {summary['summary_text'][:100] if summary['summary_text'] else 'None'}...")
        print(f"Topics type: {type(summary['topics'])}")
        print(f"Topics value: {summary['topics']}")
        
        if summary['topics']:
            if isinstance(summary['topics'], str):
                topics_parsed = json.loads(summary['topics'])
                print(f"Parsed topics: {topics_parsed}")
            else:
                print(f"Topics already parsed: {summary['topics']}")
else:
    print("No AI summaries found in database")

db.close()