# imports

import time
import os.path

from datetime import datetime

import webapp2
import jinja2
from google.appengine.api import users
import os

from google.appengine.api.users import User
from google.appengine.ext import ndb, blobstore
from google.appengine.ext.webapp import blobstore_handlers

JINJA_ENVIRONMENT = jinja2.Environment(
loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
extensions=['jinja2.ext.autoescape'],
autoescape=True
)


#directory
#
#
class Directory(ndb.Model):
    name = ndb.StringProperty()
    superkey = ndb.KeyProperty(kind='Directory')
    owner = ndb.StringProperty()
    subkey_list = ndb.KeyProperty(kind='Directory', repeated=True)
    filekey_list = ndb.KeyProperty(kind='File', repeated=True)

#files
class File(ndb.Model):
    name = ndb.StringProperty()
    superkey = ndb.KeyProperty(kind='Directory')
    owner = ndb.StringProperty()
    blobkey = ndb.BlobKeyProperty()


# defining the MainPage class that will reside the main module.
# to handel web request webapp2.RequestHandler class is extended,
#as this has the necessary functionality for receiving and responding to web requests.

# defined a get method that takes in an argument of self to indicate that this method
# may only be called on an instance of the class.
# This method will respond to the GET HTTP

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'

# pulling the current user from the request
#if a user is already logged into the system it will  generate a
#logout url and set the logout for the template to display the right message.

        user = users.get_current_user()
        if user:
            Dir_Page(response=self.response, request=self.request).get()
            return

        url = users.create_login_url('/')
        url_string = 'Login'

        template_values = {
            'url': url,
            'url_string': url_string,
            'user': user
        }
        template = JINJA_ENVIRONMENT.get_template('main.html')
        self.response.write(template.render(template_values))


class Dir_Page(webapp2.RequestHandler):

#current directory
    pwd = {}

    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        user = users.get_current_user()
        url = users.create_logout_url('/')
        url_string = 'Logout'


        root = self.get_root(user)
        if not user.email() in Dir_Page.pwd:
            Dir_Page.pwd[user.email()]=root

        template_values = {
            'url': url,
            'url_string': url_string,
            'user': user,
            'upload_url': blobstore.create_upload_url('/upload'),
            'path': self.get_path(Dir_Page.pwd[user.email()].key),
            'subdir_list': Dir_Page.pwd[user.email()].subkey_list,
            'file_list': Dir_Page.pwd[user.email()].filekey_list,
            'pwd': Dir_Page.pwd[user.email()]
        }
        template = JINJA_ENVIRONMENT.get_template('directory.html')
        self.response.write(template.render(template_values))

    def get_root(self, user):
        root = self.find_dir('root',None,user)
        if not root:
            root = [self.create_dir('root',None,user)]
        return root[0]


    #creating directory
    def create_dir(self, name, superkey, user):
        if self.find_dir(name,superkey,user):
            return

        dir = Directory(owner=user.email(), name=name, superkey=superkey)
        dir.put()
        if superkey:
            super_dir = superkey.get()
            super_dir.subkey_list.append(dir.key)
            super_dir.put()

        time.sleep(1)
        return dir

    #finding directory
    def find_dir(self, name, superkey, user):
        dir = Directory.query(ndb.AND(
            Directory.owner == user.email(),
            Directory.name == name,
            Directory.superkey == superkey)
            ).fetch()
        return dir

    #deleting directory
    def delete_dir(self, name, superkey, user):
        dir = self.find_dir(name, superkey, user)[0]
        if not dir:
            return

        super_dir = superkey.get()
        del super_dir.subkey_list[super_dir.subkey_list.index(dir.key)]
        dir.key.delete()
        super_dir.put()
        time.sleep(1)

    #renaming directory
    def rename_dir(self, name, superkey, user, new_name):
        dir = self.find_dir(name, superkey, user)[0]
        if not dir:
            return
        dir.name = new_name
        dir.put()

        time.sleep(1)
        return dir

    def find_file(self, name, superkey, user):
        file = File.query(ndb.AND(File.owner == user.email(),
                                  File.name == name,
                                  File.superkey == superkey)
                              ).fetch()
        return file
    #
    #
    def create_file(self, upload, superkey, user):

        blobinfo = blobstore.BlobInfo(upload.key())
        name = blobinfo.filename
        if self.find_file(name, superkey, user):
            return
        file = File(owner=user.email(), name=name, blobkey=blobinfo.key(), superkey=superkey)
        file.put()

        super_dir = superkey.get()
        super_dir.filekey_list.append(file.key)
        super_dir.put()

        time.sleep(1)
        return file


    #deleting file
    def delete_file(self, name, superkey, user):

        file = self.find_file(name, superkey, user)[0]
        if not file:
            return

        super_dir = superkey.get()
        del super_dir.filekey_list[super_dir.filekey_list.index(file.key)]
        file.key.delete()
        super_dir.put()
        time.sleep(1)

    def size(self, name, superkey, user):

        file = self.find_file(name, superkey,user)[0]

        super_dir =superkey.get()
        st = os.stat(name)
        return st.st_size
        time.sleep(1)




    # file properties
    #def file_properties(self, name, superkey, user):

    #    file = self.find_file(name, superkey, user)[0]
    #    if not file:
    #        return

    #    super_dir = superkey.get()

    #    time.ctime(os.path.getatime(__file__))
        #time.ctime(os.path.getmtime(__file__))
        #time.ctime(os.path.getctime(__file__))
        #file.path.getsize(__file__)

    #    super_dir.put()
    #    time.sleep(1)


    #renaming file
    def rename_file(self, name, superkey, user, new_name):
        file = self.find_file(name, superkey, user)[0]
        if not file:
            return

        file.name = new_name
        file.put()

        time.sleep(1)
        return dir

    def get_path(self, dirkey):
        if dirkey.get().name == 'root':
            return '/'
        return self.get_path(dirkey.get().superkey) + dirkey.get().name+"/"



class Open_Dir(Dir_Page):

    def post(self):
        user = users.get_current_user()
        if self.request.get('make_dir'):
            self.create_dir(self.request.get('make_dir'), Dir_Page.pwd[user.email()].key, user)
            Dir_Page.pwd[user.email()] = Dir_Page.pwd[user.email()].key.get()
            super(Open_Dir,self).get()
            return

        if self.request.get('rename_dir'):
            self.rename_dir(self.request.get('rename_dir'), Dir_Page.pwd[user.email()].key, user,self.request.get('new_name'))
            Dir_Page.pwd[user.email()] = Dir_Page.pwd[user.email()].key.get()
            super(Open_Dir,self).get()
            return

        if self.request.get('rename_file'):
            self.rename_file(self.request.get('rename_file'), Dir_Page.pwd[user.email()].key, user,self.request.get('new_name'))
            Dir_Page.pwd[user.email()] = Dir_Page.pwd[user.email()].key.get()
            super(Open_Dir,self).get()
            return

    def get(self):
        user = users.get_current_user()

        if self.request.get('change_dir'):
            if self.request.get('change_dir') == '../':
                Dir_Page.pwd[user.email()] = Dir_Page.pwd[user.email()].superkey.get()
            else:
                Dir_Page.pwd[user.email()] = self.find_dir(self.request.get('change_dir'), Dir_Page.pwd[user.email()].key, user)[0]
            super(Open_Dir, self).get()
            return

        if self.request.get('delete_dir'):
            self.delete_dir(self.request.get('delete_dir'),Dir_Page.pwd[user.email()].key,user)
            Dir_Page.pwd[user.email()] = Dir_Page.pwd[user.email()].key.get()
            super(Open_Dir, self).get()
            return

        if self.request.get('delete_file'):
            self.delete_file(self.request.get('delete_file'),Dir_Page.pwd[user.email()].key,user)
            Dir_Page.pwd[user.email()] = Dir_Page.pwd[user.email()].key.get()
            super(Open_Dir, self).get()
            return


# The post() function pull whatever that was uploaded to the blobstore.
class UploadHandler(blobstore_handlers.BlobstoreUploadHandler, Dir_Page):
    def post(self):
        user = users.get_current_user()
        upload = self.get_uploads()[0]

        super_dir = Dir_Page.pwd[user.email()]
        self.create_file(upload,super_dir.key,user)

        Dir_Page.pwd[user.email()] = Dir_Page.pwd[user.email()].key.get()
        self.redirect('/')

# BlobstoreDownloadHandler class implements the functionality for connecting to the
#blobstore and getting the file. The get() function does this.
class DownloadHandler(blobstore_handlers.BlobstoreDownloadHandler, Dir_Page):
    def get(self):
        user = users.get_current_user()

        download = self.request.get('download')
        super_dir = Dir_Page.pwd[user.email()]
        file = self.find_file(download,super_dir.key,user)[0]
        self.send_blob(file.blobkey)


# defining the application object that is responsible for this application.
app = webapp2.WSGIApplication([
('/', MainPage),
('/directory', Dir_Page),
('/open', Open_Dir),
('/upload', UploadHandler),
('/download', DownloadHandler)
], debug=True)
