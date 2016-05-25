from application import Action

class StaticAction(Action):
    def download_files(self, filename):
        return self.file_service.get_file(filename)