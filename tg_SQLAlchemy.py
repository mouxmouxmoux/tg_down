from sqlalchemy import Column, Integer, String
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


class Lines2down:
    __tablename__ = 'lines2down'
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(Integer)
    channel_username = Column(String)
    file_name = Column(String)
    offsite_id = Column(Integer)
    status = Column(Integer)


class Database:
    def __init__(self):
        self.engine = create_engine('mysql+pymysql://<username>:<password>@<host>/<database_name>', echo=True)
        self.Session = sessionmaker(bind=self.engine)
        self.Base = declarative_base()

    def create_table(self):
        self.Base.metadata.create_all(self.engine)

    def add_line2down(self, id, channel_id, channel_username, file_name, offsite_id, status):
        session = self.Session()
        line2down = Lines2down(id=id, channel_id=channel_id, channel_username=channel_username, file_name=file_name,
                               offsite_id=offsite_id, status=status)
        session.add(line2down)
        session.commit()

    def get_line2down(self):
        session = self.Session()
        line2down = session.query(Lines2down).all()
        return line2down

    def update_line2down(self, id, channel_id=None, channel_username=None, file_name=None, offsite_id=None,
                         status=None):
        session = self.Session()
        line2down = session.query(Lines2down).filter_by(id=id).first()
        if channel_id:
            line2down.channel_id = channel_id
        if channel_username:
            line2down.channel_username = channel_username
        if file_name:
            line2down.file_name = file_name
        if offsite_id:
            line2down.offsite_id = offsite_id
        if status:
            line2down.status = status

        session.commit()

    def delete_line2down(self, id):
        session = self.Session()
        line2down = session.query(Lines2down).filter_by(id=id).first()
        session.delete(line2down)
        session.commit()

    def query_line2down(self, **kwargs):
        session = self.Session()
        line2down = session.query(Lines2down).filter_by(**kwargs).all()
        return line2down


if __name__ == '__main__':
    # db = Database()
    # db.create_table()
    # db.add_line2down('John', 25)
    # db.add_line2down('Jane', 22)
    # line2down = db.get_line2down()
    # Query users by name
    # users_by_name = db.query_users(name='John')
    # print(users_by_name)
    # print(line2down)
    print('OK')
