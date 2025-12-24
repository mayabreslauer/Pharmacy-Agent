FROM nginx:alpine

# העתקת קבצי Frontend לתוך nginx
COPY . /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
