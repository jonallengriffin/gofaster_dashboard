import templeton.handlers
import templeton.middleware
import handlers
import web

#Append /api to all controllers
urls = templeton.handlers.load_urls(handlers.urls)

#Uncomment line below if you don't want to append /api
#urls = handlers.urls

app = web.application(urls, handlers.__dict__)

if __name__ == '__main__':
    app.run()
