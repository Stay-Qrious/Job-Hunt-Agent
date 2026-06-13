import sqlite3

DB_NAME = "job_hunt_cache.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_tracker (
            job_id TEXT PRIMARY KEY,
            company TEXT,
            status TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portal_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            source_tag TEXT,
            portal_url TEXT UNIQUE,
            extracted_target_url TEXT,
            status TEXT DEFAULT 'PENDING',
            is_mass_hiring INTEGER DEFAULT 0,
            raw_snippet TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def is_job_processed(job_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM job_tracker WHERE job_id = ?", (job_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def log_job(job_id, company, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO job_tracker (job_id, company, status) VALUES (?, ?, ?)", (job_id, company, status))
    conn.commit()
    conn.close()

def enqueue_portal(company, source_tag, portal_url, is_mass=0, snippet=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO portal_queue (company, source_tag, portal_url, is_mass_hiring, raw_snippet) 
            VALUES (?, ?, ?, ?, ?)
        """, (company, source_tag, portal_url, is_mass, snippet))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_extracted_target(item_id, target_url, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE portal_queue 
        SET extracted_target_url = ?, status = ? 
        WHERE id = ?
    """, (target_url, status, item_id))
    conn.commit()
    conn.close()