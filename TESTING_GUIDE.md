# CivicForge Testing Guide
*After Database Abstraction Refactoring*

## 🚀 Quick Test - SQLite (Default)

```bash
# 1. Set up environment
cd /Users/victor/Projects/civicforge
export BOARD_DB_PATH=/Users/victor/Projects/civicforge/board.db
export CIVICFORGE_SECRET_KEY=test-secret-key-at-least-32-characters-long

# 2. Run migrations
python -m src.board_mvp.migrations_pg

# 3. Start the server
uvicorn src.board_mvp.web:app --reload

# 4. In another terminal, seed data
python -m src.board_mvp.seed_tasks

# 5. Test endpoints
# Using Python urllib (preferred - no external dependencies)
python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
# Should return: {"status":"healthy","database":"connected"}

# Note: Use Python urllib instead of curl for all health checks and tests

# 6. Open browser
# Go to http://localhost:8000
# Login with: admin/admin123 or dev/dev123
```

## 🐘 Test with PostgreSQL (Docker)

```bash
# 1. Start PostgreSQL with docker-compose
docker-compose up postgres -d

# 2. Set up environment for PostgreSQL
export DATABASE_URL=postgresql://civicforge:civicforge_dev_password@localhost:5432/civicforge_db
export CIVICFORGE_SECRET_KEY=test-secret-key-at-least-32-characters-long

# 3. Run migrations
python -m src.board_mvp.migrations_pg

# 4. Start the server
uvicorn src.board_mvp.web:app --reload

# 5. Seed data and test (same as SQLite steps 4-6)
```

## 🧪 Test Database Compatibility

### Test 1: Basic Operations
```bash
# Create a test script
cat > test_db.py << 'EOF'
from src.board_mvp.database import Database

# Test with SQLite
db_sqlite = Database("sqlite:///test.db")
db_sqlite.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
db_sqlite.execute("INSERT INTO test (name) VALUES (?)", ("SQLite Test",))
result = db_sqlite.fetchone("SELECT * FROM test WHERE name = ?", ("SQLite Test",))
print(f"SQLite test: {result}")
db_sqlite.close()

# Test with PostgreSQL (if available)
try:
    db_pg = Database("postgresql://civicforge:civicforge_dev_password@localhost:5432/civicforge_db")
    db_pg.execute("CREATE TABLE IF NOT EXISTS test (id SERIAL PRIMARY KEY, name TEXT)")
    db_pg.execute("INSERT INTO test (name) VALUES (?)", ("PostgreSQL Test",))
    result = db_pg.fetchone("SELECT * FROM test WHERE name = ?", ("PostgreSQL Test",))
    print(f"PostgreSQL test: {result}")
    db_pg.close()
except Exception as e:
    print(f"PostgreSQL test skipped: {e}")
EOF

python test_db.py
```

### Test 2: API Endpoints
```bash
# Test registration
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123","real_name":"Test User","role":"Participant"}'

# Test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'

# Save the token from login response, then test authenticated endpoint
TOKEN="your-token-here"
curl -X GET http://localhost:8000/api/me \
  -H "Authorization: Bearer $TOKEN"
```

### Test 3: Full Quest Lifecycle
```python
# Create test_quest_lifecycle.py
import requests
import json

API_BASE = "http://localhost:8000/api"

# 1. Login as admin
resp = requests.post(f"{API_BASE}/auth/login", json={"username": "admin", "password": "admin123"})
admin_token = resp.json()["token"]

# 2. Create a quest
resp = requests.post(
    f"{API_BASE}/quests",
    json={"title": "Test Quest", "description": "Testing the system", "category": "general"},
    headers={"Authorization": f"Bearer {admin_token}"}
)
quest_id = resp.json()["id"]
print(f"Created quest {quest_id}")

# 3. Login as dev
resp = requests.post(f"{API_BASE}/auth/login", json={"username": "dev", "password": "dev123"})
dev_token = resp.json()["token"]

# 4. Claim the quest
resp = requests.post(
    f"{API_BASE}/quests/{quest_id}/claim",
    headers={"Authorization": f"Bearer {dev_token}"}
)
print(f"Claimed quest: {resp.json()}")

# 5. Submit work
resp = requests.post(
    f"{API_BASE}/quests/{quest_id}/submit",
    json={"work_proof": "I completed the test"},
    headers={"Authorization": f"Bearer {dev_token}"}
)
print(f"Submitted work: {resp.json()}")

# 6. Verify as admin
resp = requests.post(
    f"{API_BASE}/quests/{quest_id}/verify",
    json={"result": "EXCEPTIONAL"},
    headers={"Authorization": f"Bearer {admin_token}"}
)
print(f"Verified quest: {resp.json()}")

# 7. Check stats
resp = requests.get(f"{API_BASE}/stats/board")
print(f"Board stats: {json.dumps(resp.json(), indent=2)}")
```

## 🔍 Verify Database Switch

### Check which database is being used:
```python
from src.board_mvp.database import get_db

db = get_db()
print(f"Using: {db.connection_string}")
print(f"Adapter: {type(db.adapter).__name__}")
```

### PostgreSQL-specific test:
```sql
-- Connect to PostgreSQL
psql postgresql://civicforge:civicforge_dev_password@localhost:5432/civicforge_db

-- Check tables
\dt

-- Check data
SELECT * FROM users;
SELECT * FROM quests;
SELECT * FROM experience_ledger;
```

## ⚠️ Common Issues

### Issue: "psycopg2 not installed"
```bash
pip install psycopg2-binary
```

### Issue: "PostgreSQL connection refused"
```bash
# Make sure PostgreSQL is running
docker-compose ps
# If not running:
docker-compose up postgres -d
```

### Issue: "Database does not exist"
```bash
# Create database manually
docker exec -it civicforge_postgres_1 psql -U civicforge -c "CREATE DATABASE civicforge_db;"
```

### Issue: "SECRET_KEY not set"
```bash
# Set a proper secret key
export CIVICFORGE_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

## ✅ Success Indicators

1. **Health check passes**: 
   ```python
   python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
   ```
   Returns healthy status
2. **Can switch databases**: Set DATABASE_URL for PostgreSQL, unset for SQLite
3. **All features work**: Registration, login, quest lifecycle, stats
4. **No SQL errors**: Queries work on both databases
5. **Performance**: Similar response times for both databases

## 🎯 Next Steps After Testing

1. **Deploy to staging** with PostgreSQL
2. **Run load tests** to verify connection pooling
3. **Monitor logs** for any database-specific issues
4. **Backup strategy** for PostgreSQL in production