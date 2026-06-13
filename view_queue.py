import sqlite3

conn = sqlite3.connect("job_hunt_cache.db")
cursor = conn.cursor()
cursor.execute("""
    SELECT id, company, source_tag, is_mass_hiring, portal_url 
    FROM portal_queue 
    ORDER BY timestamp DESC
""")
rows = cursor.fetchall()
conn.close()

print(f"\n=====================================================================================")
print(f"                       CENTRALIZED DATA LEDGER STORAGE VIEW")
print(f"=====================================================================================")
print(f"{'ID':<4} | {'COMPANY':<25} | {'SOURCE CHANNEL':<25} | {'MASS?':<5} | {'TARGET LINK'}")
print("-" * 115)

for id_val, company, source, mass, url in rows:
    mass_status = "YES" if mass == 1 else "NO"
    print(f"{id_val:<4} | {company.upper():<25} | {source:<25} | {mass_status:<5} | {url[:50]}")