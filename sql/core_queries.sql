-- Core SQL aggregations for the Netflix content analysis (SQLite syntax)
-- Tables: netflix_titles (one row per title), title_genres (one row per title-genre pair),
--         title_countries (one row per title-country pair)

-- Q1: Titles added per year, by type (growth story)
SELECT year_added, type, COUNT(*) AS titles
FROM netflix_titles
WHERE year_added >= 2012
GROUP BY year_added, type
ORDER BY year_added, type;

-- Q2: Top 10 genres (join through the bridge table)
SELECT genre, COUNT(*) AS titles
FROM title_genres
GROUP BY genre
ORDER BY titles DESC
LIMIT 10;

-- Q3: Genre share by year added (which genres are gaining ground?)
SELECT t.year_added, g.genre,
       COUNT(*) AS titles,
       ROUND(COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY t.year_added), 3) AS share
FROM title_genres g
JOIN netflix_titles t ON t.show_id = g.show_id
WHERE t.year_added >= 2014
GROUP BY t.year_added, g.genre
ORDER BY t.year_added, share DESC;

-- Q4: Top 10 countries by number of titles (all listed countries counted)
SELECT country, COUNT(*) AS titles
FROM title_countries
WHERE country <> 'Unknown'
GROUP BY country
ORDER BY titles DESC
LIMIT 10;

-- Q5: Maturity rating mix for the top 5 primary countries
SELECT primary_country, rating, COUNT(*) AS titles
FROM netflix_titles
WHERE primary_country IN (
    SELECT primary_country FROM netflix_titles
    WHERE primary_country <> 'Unknown'
    GROUP BY primary_country ORDER BY COUNT(*) DESC LIMIT 5)
GROUP BY primary_country, rating
ORDER BY primary_country, titles DESC;

-- Q6: Share of TV shows with only one season
SELECT ROUND(AVG(CASE WHEN seasons = 1 THEN 1.0 ELSE 0 END), 3) AS one_season_share,
       COUNT(*) AS tv_shows
FROM netflix_titles
WHERE type = 'TV Show';

-- Q7: Average movie length by release year (2000 onward)
SELECT release_year, ROUND(AVG(minutes), 1) AS avg_minutes, COUNT(*) AS movies
FROM netflix_titles
WHERE type = 'Movie' AND release_year >= 2000
GROUP BY release_year
ORDER BY release_year;
