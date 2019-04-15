import time

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


class File(ndb.Model):
    name = ndb.StringProperty()
    superkey = ndb.KeyProperty(kind='Directory')
    owner = ndb.StringProperty()
    blobkey = ndb.BlobKeyProperty()


class Directory(ndb.Model):
    name = ndb.StringProperty()
    superkey = ndb.KeyProperty(kind='Directory')
    owner = ndb.StringProperty()
    subkey_list = ndb.KeyProperty(kind='Directory', repeated=True)
    filekey_list = ndb.KeyProperty(kind='File', repeated=True)


class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        user = users.get_current_user()
        if user:
            DirPage(response=self.response, request=self.request).get()
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


class DirPage(webapp2.RequestHandler):

    pwd = {}

    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        user = users.get_current_user()
        url = users.create_logout_url('/')
        url_string = 'Logout'

             # if not user:
        #     MainPage(response=self.response, request=self.request).get()
        #     return

        root = self.get_root(user)
        if not user.email() in DirPage.pwd:
            DirPage.pwd[user.email()]=root

        template_values = {
            'url': url,
            'url_string': url_string,
            'user': user,
            'upload_url': blobstore.create_upload_url('/upload'),
            'path': self.get_path(DirPage.pwd[user.email()].key),
            'subdir_list': DirPage.pwd[user.email()].subkey_list,
            'file_list': DirPage.pwd[user.email()].filekey_list,
            'pwd': DirPage.pwd[user.email()]
        }
        template = JINJA_ENVIRONMENT.get_template('directory.html')
        self.response.write(template.render(template_values))

    def get_root(self, user):
        root = self.find_dir('root',None,user)
        if not root:
            root = [self.create_dir('root',None,user)]
        return root[0]

    def find_dir(self, name, superkey, user):
        dir = Directory.query(ndb.AND(Directory.owner == user.email(),
                                       Directory.name == name,
                                      Directory.superkey == superkey)
                               ).fetch()
        return dir

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
    def rename_dir(self, name, superkey, user, newname):
        dir = self.find_dir(name, superkey, user)[0]
        if not dir:
            return
        dir.name = newname
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

    #renaming file
    def rename_file(self, name, superkey, user, newname):
        file = self.find_file(name, superkey, user)[0]
        if not file:
            return

        file.name = newname
        file.put()

        time.sleep(1)
        return dir

    def get_path(self, dirkey):
        if dirkey.get().name == 'root':
            return '/'
        return self.get_path(dirkey.get().superkey) + dirkey.get().name+"/"



class DirOp(DirPage):

    def post(self):
        user = users.get_current_user()
        if self.request.get('mkdir'):
            self.create_dir(self.request.get('mkdir'), DirPage.pwd[user.email()].key, user)
            DirPage.pwd[user.email()] = DirPage.pwd[user.email()].key.get()
            super(DirOp,self).get()
            return

        if self.request.get('rendir'):
            self.rename_dir(self.request.get('rendir'), DirPage.pwd[user.email()].key, user,self.request.get('new_name'))
            DirPage.pwd[user.email()] = DirPage.pwd[user.email()].key.get()
            super(DirOp,self).get()
            return

        if self.request.get('renfile'):
            self.rename_file(self.request.get('renfile'), DirPage.pwd[user.email()].key, user,self.request.get('new_name'))
            DirPage.pwd[user.email()] = DirPage.pwd[user.email()].key.get()
            super(DirOp,self).get()
            return

    def get(self):
        user = users.get_current_user()

        if self.request.get('change_dir'):
            if self.request.get('change_dir') == '../':
                DirPage.pwd[user.email()] = DirPage.pwd[user.email()].superkey.get()
            else:
                DirPage.pwd[user.email()] = self.find_dir(self.request.get('change_dir'), DirPage.pwd[user.email()].key, user)[0]
            super(DirOp, self).get()
            return

        if self.request.get('delete_dir'):
            self.delete_dir(self.request.get('delete_dir'),DirPage.pwd[user.email()].key,user)
            DirPage.pwd[user.email()] = DirPage.pwd[user.email()].key.get()
            super(DirOp, self).get()
            return

        if self.request.get('delete_file'):
            self.delete_file(self.request.get('delete_file'),DirPage.pwd[user.email()].key,user)
            DirPage.pwd[user.email()] = DirPage.pwd[user.email()].key.get()
            super(DirOp, self).get()
            return


class UploadHandler(blobstore_handlers.BlobstoreUploadHandler, DirPage):
    def post(self):
        user = users.get_current_user()
        upload = self.get_uploads()[0]
        super_dir = DirPage.pwd[user.email()]
        self.create_file(upload,super_dir.key,user)
        DirPage.pwd[user.email()] = DirPage.pwd[user.email()].key.get()
        self.redirect('/')

class DownloadHandler(blobstore_handlers.BlobstoreDownloadHandler, DirPage):
    def get(self):
        user = users.get_current_user()
        download = self.request.get('download')
        super_dir = DirPage.pwd[user.email()]
        file = self.find_file(download,super_dir.key,user)[0]
        self.send_blob(file.blobkey)

app = webapp2.WSGIApplication([
('/', MainPage),
('/directory', DirPage),
('/op', DirOp),
('/upload', UploadHandler),
('/download', DownloadHandler),
], debug=True)
