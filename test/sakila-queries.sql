USE sakila;
-- List all film titles.
SELECT title FROM film;
-- Show the first and last name of all actors.
SELECT first_name,last_name FROM actor;
-- List all categories.
SELECT * FROM category;
-- Display the first 10 customers.
SELECT * FROM customer ORDER BY customer_id LIMIT 10 ;
-- Show all unique ratings available in the film table.
SELECT DISTINCT rating FROM film;
-- Find all films with a rental rate greater than $2.
SELECT title, rental_rate FROM film WHERE rental_rate >2 ORDER BY film_id;
-- List films released in the year 2006.
SELECT  title, release_year FROM film WHERE release_year = 2006;
-- LIST ALL FILMS WITH LENGTH BETWEEN 90 AND 120 MINUTES.
SELECT title, length,film_id FROM film WHERE length  BETWEEN 90 AND 120 ORDER BY film_id;
-- Find all customers whose last name starts with ‘S’.
SELECT first_name, last_name FROM customer WHERE last_name LIKE 'S%';
-- Show customers living in the city 'Dallas'.
SELECT c.customer_id, c.first_name, c.last_name, ct.city FROM customer c 
JOIN address a ON c.address_id = a.address_id 
JOIN city ct ON a.city_id = ct.city_id WHERE ct.city = 'Dallas';
-- Show the titles of films and their category names.
SELECT c.category_id, c.name AS category_name, f.film_id, f.title FROM category c
JOIN film_category fc ON c.category_id = fc.category_id
JOIN film f ON fc.film_id = f.film_id;
-- List all payments along with the customer’s first and last name.
SELECT p.payment_id, p.amount as amount_pay, c.first_name, c.last_name FROM payment p
JOIN customer c ON c.customer_id =p.customer_id;
-- Display staff names and the stores they work in.
SELECT st.staff_id, st.first_name, st.last_name, st.active as staff_details ,s.store_id ,s.manager_staff_id FROM staff st
JOIN store s ON st.store_id = s.store_id;
-- List film titles and the language they’re in.
SELECT fi.film_id, fi.title, las.name, las.language_id, las.name AS language_name FROM film fi
JOIN language las ON fi.language_id = las.language_id;
-- Find rental date and return date for each rental, along with customer name.
SELECT r.rental_id, r.rental_date, r.return_date, c.customer_id, c.first_name, c.last_name FROM rental r
JOIN customer c ON c.customer_id = r.customer_id;
-- Count the number of films in each category.
SELECT c.name AS category_name, COUNT(fc.film_id) AS film_count FROM category c
JOIN film_category fc ON c.category_id = fc.category_id 
GROUP BY c.name;
-- Find the average rental rate of films in each category.
SELECT c.name AS category_name,ROUND(AVG(f.rental_rate),2) AS avg_rental_rate FROM category c
JOIN film_category fc ON c.category_id =fc.category_id
JOIN film f ON fc.film_id =f.film_id
GROUP BY c.name;
-- List the number of rentals per customer.
SELECT c.customer_id, CONCAT(c.first_name, ' ',c.last_name) as customer_name, COUNT(r.rental_id) AS rental_count FROM customer c
JOIN rental r ON c.customer_id = r.customer_id
GROUP BY c.customer_id,c.first_name,c.last_name;
-- Find the highest payment amount made by any customer.
SELECT * FROM payment;
SELECT customer_id ,MAX(AMOUNT) AS highest_payment
FROM payment
GROUP BY customer_id;
-- Show total revenue (sum of amount) per store.
SELECT s.store_id, SUM(p.amount) AS total_revenue FROM store s
JOIN staff st ON s.store_id = st.store_id
JOIN payment p ON st.staff_id = p.staff_id
GROUP BY s.store_id;
-- List top 5 longest films.
SELECT film_id ,title,length FROM film
ORDER by length  DESC
LIMIT 5 ;
-- Show top 10 customers who spent the most.
SELECT c.customer_id, CONCAT(c.first_name, ' ', c.last_name) AS customer_name, SUM(p.amount) AS total_spent FROM customer c
JOIN payment p ON c.customer_id = p.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name
ORDER BY total_spent DESC
LIMIT 10;
-- Find top 3 most rented films.
SELECT f.title, COUNT(*) AS rental_count FROM rental r
JOIN inventory i ON r.inventory_id = i.inventory_id
JOIN film f ON i.film_id = f.film_id
GROUP BY f.title
ORDER BY rental_count DESC
LIMIT 3;
-- Display actors sorted by last name in descending order.
SELECT actor_id, first_name, last_name FROM actor
ORDER BY last_name DESC;
-- List films sorted by length (shortest to longest).
SELECT film_id, title, length FROM film
ORDER BY length ASC;
-- Find films whose rental rate is above the average rental rate.
SELECT title, rental_rate FROM film
WHERE rental_rate > (
    SELECT AVG(rental_rate) FROM film
);
-- Find customers who have made more payments than the average number of payments.
SELECT c.customer_id, c.first_name, c.last_name, COUNT(p.payment_id) AS num_payments
FROM customer c
JOIN payment p ON c.customer_id = p.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name
HAVING COUNT(p.payment_id) > (
    SELECT AVG(payment_count)
    FROM (
        SELECT COUNT(*) AS payment_count
        FROM payment
        GROUP BY customer_id
    ) AS sub
);
-- Find films that are not rented by anyone.
SELECT film_id, title FROM film
WHERE film_id NOT IN (
    SELECT DISTINCT i.film_id
    FROM inventory i
    JOIN rental r ON i.inventory_id = r.inventory_id
);
-- Show actors who acted in more than 10 films.
SELECT a.actor_id, a.first_name, a.last_name, COUNT(fa.film_id) AS film_count FROM actor a
JOIN film_actor fa ON a.actor_id = fa.actor_id
GROUP BY a.actor_id, a.first_name, a.last_name
HAVING COUNT(fa.film_id) > 10;
-- Find customers who rented ‘ACADEMY DINOSAUR’.
SELECT DISTINCT c.customer_id, c.first_name, c.last_name
FROM customer c
JOIN rental r ON c.customer_id = r.customer_id
JOIN inventory i ON r.inventory_id = i.inventory_id
JOIN film f ON i.film_id = f.film_id
WHERE f.title = 'ACADEMY DINOSAUR';
-- Use a CTE to find the number of films per category, then show only categories with more than 60 films.
WITH film_count AS (
    SELECT c.name AS category_name, COUNT(f.film_id) AS num_films
    FROM category c
    JOIN film_category fc ON c.category_id = fc.category_id
    JOIN film f ON fc.film_id = f.film_id
    GROUP BY c.name
)
SELECT * FROM film_count WHERE num_films > 60;
-- Write a recursive CTE to list numbers 1 to 10.
WITH RECURSIVE numbers AS (
    SELECT 1 AS n
    UNION ALL
    SELECT n + 1 FROM numbers WHERE n < 10
)
SELECT n FROM numbers;
-- Use a CTE to get the top 5 most rented films and then list their titles and rental counts.
WITH rental_counts AS (
    SELECT f.film_id, f.title, COUNT(*) AS rental_count
    FROM film f
    JOIN inventory i ON f.film_id = i.film_id
    JOIN rental r ON i.inventory_id = r.inventory_id
    GROUP BY f.film_id, f.title
    ORDER BY rental_count DESC
    LIMIT 5
)
SELECT * FROM rental_counts;
-- Use a CTE to find the total payments per customer and list only those over $100.
WITH customer_payments AS (
    SELECT c.customer_id, CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
           SUM(p.amount) AS total_payment
    FROM customer c
    JOIN payment p ON c.customer_id = p.customer_id
    GROUP BY c.customer_id, c.first_name, c.last_name
)
SELECT * FROM customer_payments WHERE total_payment > 100;
-- Create a CTE that lists actors and the number of films they acted in.
WITH actor_films AS (
    SELECT a.actor_id, a.first_name, a.last_name, COUNT(fa.film_id) AS film_count
    FROM actor a
    JOIN film_actor fa ON a.actor_id = fa.actor_id
    GROUP BY a.actor_id, a.first_name, a.last_name
)
SELECT * FROM actor_films;
