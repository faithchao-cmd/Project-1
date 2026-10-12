import os, sqlite3, re
import pandas as pd

# Run from the project root: python Notes/build_db.py
CSV = "dataset/netflix_titles.csv"
SQL_FILE = "sql/core_queries.sql"
DB = "netflix.db"
assert os.path.exists(CSV), f"Missing {CSV}. Run this from the Project-1 folder."
assert os.path.exists(SQL_FILE), f"Missing {SQL_FILE}."

# ---- Clean (same steps as the analysis script) ----
df = pd.read_csv(CSV).drop_duplicates()
df["date_added"] = pd.to_datetime(df["date_added"].str.strip(), errors="coerce", format="mixed")
df["year_added"] = df["date_added"].dt.year
df["date_added"] = df["date_added"].dt.strftime("%Y-%m-%d")
df["country"] = df["country"].fillna("Unknown")
df["primary_country"] = df["country"].str.split(",").str[0].str.strip()
df["minutes"] = df.loc[df["type"] == "Movie", "duration"].str.extract(r"(\d+)", expand=False).astype(float)
df["seasons"] = df.loc[df["type"] == "TV Show", "duration"].str.extract(r"(\d+)", expand=False).astype(float)
bad = df["rating"].astype(str).str.contains("min", na=False)
df.loc[bad, "rating"] = "Unknown"
df["rating"] = df["rating"].fillna("Unknown")

# ---- Bridge tables: one row per title-genre / title-country pair ----
genres = (df.assign(genre=df["listed_in"].str.split(", "))
            .explode("genre", ignore_index=True)[["show_id", "genre"]])
countries = (df.assign(country=df["country"].str.split(","))
               .explode("country", ignore_index=True)[["show_id", "country"]])
countries["country"] = countries["country"].str.strip()
countries = countries[countries["country"] != ""]

# ---- Write the database ----
if os.path.exists(DB):
    os.remove(DB)
conn = sqlite3.connect(DB)
df.to_sql("netflix_titles", conn, index=False)
genres.to_sql("title_genres", conn, index=False)
countries.to_sql("title_countries", conn, index=False)
print(f"Built {DB}: {len(df)} titles, {len(genres)} genre rows, {len(countries)} country rows\n")

# ---- Run every query in the .sql file and print the result ----
sql_text = open(SQL_FILE).read()
pd.set_option("display.width", 200)
for block in [b.strip() for b in sql_text.split(";") if b.strip()]:
    title = re.search(r"--\s*(Q\d+:.*)", block)
    query = "\n".join(l for l in block.splitlines() if not l.strip().startswith("--")).strip()
    if not query.upper().startswith("SELECT"):
        continue
    print("=" * 70)
    print(title.group(1) if title else query[:60])
    print(pd.read_sql_query(query, conn).head(15).to_string(index=False))
    print()
conn.close()
