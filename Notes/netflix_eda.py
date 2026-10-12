import matplotlib
matplotlib.use("Agg")  # save charts to files, no window needed


# %% [markdown]
# # OTT Streaming Content Trend Analysis (Netflix)
# Run all cells top to bottom (**Run All**). Charts are saved to `outputs/charts/`.
# 
# **Business question:** What is in Netflix's catalog, how has it changed, and what should a content acquisition team greenlight next?

# %% [markdown]
# ## 0. Setup

# %%
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (10, 5)

# Find the CSV automatically (works whether the notebook is in Notes/ or the project root)
candidates = ["../dataset/netflix_titles.csv", "dataset/netflix_titles.csv",
              "../data/netflix_titles.csv", "netflix_titles.csv"]
DATA_PATH = next((p for p in candidates if os.path.exists(p)), None)
assert DATA_PATH, f"CSV not found. Current folder: {os.getcwd()}"

# Charts folder sits next to the dataset folder, created if missing
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(DATA_PATH))) if DATA_PATH.count("/") else os.getcwd()
CHART_DIR = os.path.join(ROOT, "outputs", "charts")
os.makedirs(CHART_DIR, exist_ok=True)

def save(name):
    """Save the current chart, then show it."""
    plt.tight_layout()
    plt.savefig(os.path.join(CHART_DIR, name), dpi=200, bbox_inches="tight")
    plt.show()

print("Data:", DATA_PATH)
print("Charts will be saved to:", CHART_DIR)

# %% [markdown]
# ## 1. Load and inspect

# %%
df = pd.read_csv(DATA_PATH)
print(df.shape)
print(df.isna().sum())
df.head()

# %% [markdown]
# ## 2. Clean
# - Drop duplicates, parse dates, fill missing countries, take the first listed country as the primary one (a simplification), and split `duration` into minutes (movies) and seasons (TV).
# - `rating` is the **maturity rating** (TV-MA, PG-13), not a viewer score.

# %%
df = df.drop_duplicates()

df["date_added"] = pd.to_datetime(df["date_added"].str.strip(), errors="coerce", format="mixed")
df["year_added"] = df["date_added"].dt.year
df["month_added"] = df["date_added"].dt.month

df["country"] = df["country"].fillna("Unknown")
df["primary_country"] = df["country"].str.split(",").str[0].str.strip()

df["minutes"] = df.loc[df["type"] == "Movie", "duration"].str.extract(r"(\d+)", expand=False).astype(float)
df["seasons"] = df.loc[df["type"] == "TV Show", "duration"].str.extract(r"(\d+)", expand=False).astype(float)

# Known data glitch: some rows have a duration (e.g. "74 min") in the rating column
bad = df["rating"].astype(str).str.contains("min", na=False)
df.loc[bad, "rating"] = "Unknown"
df["rating"] = df["rating"].fillna("Unknown")

df["gap"] = df["year_added"] - df["release_year"]

# One row per title-genre pair (Python version of the SQL bridge table)
genres = df.assign(genre=df["listed_in"].str.split(", ")).explode("genre", ignore_index=True)

movies = df[df["type"] == "Movie"]
shows = df[df["type"] == "TV Show"]
print("Titles:", len(df), "| Movies:", len(movies), "| TV shows:", len(shows))

# %% [markdown]
# ## 3. Visualizations

# %% [markdown]
# ### Chart 1: Movies vs TV share

# %%
type_counts = df["type"].value_counts()
plt.pie(type_counts, labels=type_counts.index, autopct="%1.1f%%", startangle=90)
plt.title("Catalog mix: Movies vs TV Shows")
save("01_type_share.png")

# %% [markdown]
# ### Chart 2: Titles added per year, by type

# %%
yearly = pd.crosstab(df["year_added"], df["type"])
yearly = yearly.loc[yearly.index >= 2012]
yearly.plot.area(alpha=0.8)
plt.title("Titles added to Netflix per year")
plt.ylabel("Number of titles")
plt.xlabel("Year added")
save("02_titles_per_year.png")

# %% [markdown]
# ### Chart 3: Top 10 genres

# %%
top_genres = genres["genre"].value_counts().head(10)
sns.barplot(x=top_genres.values, y=top_genres.index, color="steelblue")
plt.title("Top 10 genres")
plt.xlabel("Number of titles")
save("03_top_genres.png")

# %% [markdown]
# ### Chart 4: Genre share by year added (heatmap)
# Shares (not raw counts) show which genres gain ground, independent of catalog growth.

# %%
top8 = genres["genre"].value_counts().head(8).index
g = genres[genres["genre"].isin(top8) & (genres["year_added"] >= 2014)]
heat = pd.crosstab(g["year_added"], g["genre"], normalize="index")
plt.figure(figsize=(11, 5))
sns.heatmap(heat.T, annot=True, fmt=".0%", cmap="YlOrRd")
plt.title("Genre share by year added")
save("04_genre_share_heatmap.png")

# %% [markdown]
# ### Chart 5: Top countries, and how the top 5 trend over time

# %%
known = df[df["primary_country"] != "Unknown"]
top_countries = known["primary_country"].value_counts().head(10)
sns.barplot(x=top_countries.values, y=top_countries.index, color="indianred")
plt.title("Top 10 content-producing countries (primary country)")
plt.xlabel("Number of titles")
save("05a_top_countries.png")

top5 = top_countries.head(5).index
trend = pd.crosstab(known["year_added"], known["primary_country"])[top5]
trend = trend.loc[trend.index >= 2014]
trend.plot(marker="o")
plt.title("Titles added per year, top 5 countries")
plt.ylabel("Number of titles")
save("05b_country_trend.png")

# %% [markdown]
# ### Chart 6: Maturity rating mix by type

# %%
order = ["TV-Y", "TV-Y7", "TV-G", "G", "TV-PG", "PG", "PG-13", "TV-14", "R", "TV-MA", "NR", "UR", "Unknown"]
rating_mix = pd.crosstab(df["type"], df["rating"], normalize="index")
rating_mix = rating_mix[[c for c in order if c in rating_mix.columns]]
rating_mix.plot.bar(stacked=True, colormap="viridis")
plt.legend(title="Rating", bbox_to_anchor=(1, 1))
plt.title("Maturity rating mix by type")
plt.xticks(rotation=0)
save("06_rating_mix.png")

# %% [markdown]
# ### Chart 7: Movie runtime (distribution and trend)

# %%
sns.histplot(movies["minutes"].dropna(), bins=40, kde=True)
plt.axvline(movies["minutes"].median(), color="red", linestyle="--", label="Median")
plt.legend()
plt.title("Movie runtime distribution (minutes)")
save("07a_runtime_hist.png")

median_by_year = movies[movies["release_year"] >= 2000].groupby("release_year")["minutes"].median()
median_by_year.plot(marker="o")
plt.title("Median movie length by release year")
plt.ylabel("Minutes")
save("07b_runtime_trend.png")

# %% [markdown]
# ### Chart 8: Seasons per TV show

# %%
sns.countplot(x=shows["seasons"].dropna().astype(int), color="seagreen")
plt.title("TV shows by number of seasons")
plt.xlabel("Seasons")
save("08_seasons.png")
print("Share of one-season shows:", round((shows["seasons"] == 1).mean(), 3))

# %% [markdown]
# ### Chart 9: Library vs Netflix-era content
# Gap near 0 = added around release (new/original). Large gap = older licensed library content.

# %%
sns.histplot(df["gap"].dropna().clip(0, 30), bins=31)
plt.title("Years between release and arrival on Netflix")
plt.xlabel("Years")
save("09_release_gap.png")

# %% [markdown]
# ## 4. Numbers for the memo

# %%
print("Type share:\n", df["type"].value_counts(normalize=True).round(3), "\n")
print("Top genres:\n", top_genres, "\n")
print("Top countries:\n", top_countries, "\n")
print("Median movie length (min):", movies["minutes"].median())
print("One-season TV share:", round((shows["seasons"] == 1).mean(), 3))
print("Share TV-MA + TV-14:", round(df["rating"].isin(["TV-MA", "TV-14"]).mean(), 3))
print("Share of titles added within 2 years of release:", round((df["gap"] <= 2).mean(), 3))
intl = genres["genre"].str.contains("International", na=False)
print("Share of genre tags that are 'International':", round(intl.mean(), 3))

# %% [markdown]
# ## 5. Content strategy memo (fill in with YOUR numbers from above)
# 
# 1. **International content:** *finding + number + recommendation*
# 2. **Limited series vs long-running shows:** *finding + number + recommendation*
# 3. **Family/kids gap:** *finding + number + recommendation*
# 
# **Limitations:** dataset has no viewership data; `rating` is maturity rating, not quality; only the first listed country is used.
