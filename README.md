# FlaskWebApp
First web app, written from Traversy Media YouTube tutorial.

https://www.youtube.com/watch?v=zRwy8gtgJ1A&index=1&list=PLillGF-RfqbbbPz6GSEM9hLQObuQjNoj_

Changes made:
* app.config settings moved to separate file, after attempts to load via env variables were unsuccessful
* Deployed to apache2 server on EC2, requiring start.wsgi file and use of url_for functions to replace static links
