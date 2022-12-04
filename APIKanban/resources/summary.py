from flask import jsonify, send_file, current_app
from flask_restful import Resource
from models import Bucket, Card, User
import json

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template

SMPTP_SERVER_HOST = 'localhost'
SMPTP_SERVER_PORT = 1025
SENDER_ADDRESS = 'ganesh@email.com'
SENDER_PASSWORD = ''

# from flask_mail import Message
# from mailing import mail

from db import db 
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('AGG')
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import date, datetime
import datetime as d

from caching import cache
import time
import random

from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
)

from workers import celery
from celery.schedules import crontab


@celery.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls test('hello') every 10 seconds.
    # sender.add_periodic_task(20.0, sendDailyReport.s())

    # # Calls test('world') every 30 seconds
    # sender.add_periodic_task(30.0, test.s('world'), expires=10)
    
    sender.add_periodic_task(
        crontab(day_of_month='1', hour=0, minute=1),
        sendMonthlyReport.s(),
        name= 'Monthly performance'
    )

    sender.add_periodic_task(
        crontab(hour=9, minute=1),
        sendDailyReport.s(),
        name= 'Daily reminder'
    )


@celery.task()
def sendDailyReport():
    date = datetime.now()
    # user = User.query.get(current_userid)
    users = User.query.all()
    for user in users:
        q = db.session.query(User, Bucket, Card).filter(User.id == Bucket.userid,
                                                    Bucket.id == Card.bucketid,
                                                    User.id == user.id)
        df = pd.read_sql_query(q.statement, con=db.engine)
        df.drop('password', axis=1, inplace=True)
        df['dlpassed'] = (df.deadline < pd.Timestamp('today').normalize()) & (df.iscompleted==0)
        with open('templates/dailyemail.html') as file_:
            template = Template(file_.read())
            message= template.render(user= user, df = df, date = date)
        msg = MIMEMultipart()
        msg['From'] = SENDER_ADDRESS
        msg['To'] = user.email
        msg['Subject'] = 'Reminder! Pending tasks'
        msg.attach(MIMEText(message, 'html'))
        
        s = smtplib.SMTP(host = SMPTP_SERVER_HOST, port=SMPTP_SERVER_PORT)
        s.login(SENDER_ADDRESS, SENDER_PASSWORD)
        s.send_message(msg)
        s.quit()
    return True


@celery.task()
def sendMonthlyReport():
    date = datetime.now()
    prev_first = (d.datetime.today().replace(day=1) - d.timedelta(days=1)).replace(day=1)
    prev_last = d.date.today().replace(day=1) - d.timedelta(days=1)
    last_month = format(d.date.today().replace(day=1) - d.timedelta(days=1), '%B %Y')
    # user = User.query.get(current_userid)
    users = User.query.all()
    for user in users:
        q = db.session.query(User, Bucket, Card).filter(User.id == Bucket.userid,
                                                    Bucket.id == Card.bucketid,
                                                    User.id == user.id)
        df = pd.read_sql_query(q.statement, con=db.engine)
        df = df.loc[(df['completeddate'] >= prev_first)]
        
        df.drop('password', axis=1, inplace=True)
        df['dlpassed'] = (df.deadline < pd.Timestamp('today').normalize()) & (df.iscompleted==0)
        
        
        with open('templates/monthlyemail.html') as file_:
            template = Template(file_.read())
            message= template.render(user= user, df = df, date = date, lm=last_month)
        msg = MIMEMultipart()
        msg['From'] = SENDER_ADDRESS
        msg['To'] = user.email
        msg['Subject'] = 'Your Monthly Performance Report'
        msg.attach(MIMEText(message, 'html'))
        
        s = smtplib.SMTP(host = SMPTP_SERVER_HOST, port=SMPTP_SERVER_PORT)
        s.login(SENDER_ADDRESS, SENDER_PASSWORD)
        s.send_message(msg)
        s.quit()
    return True


@jwt_required()
@cache.memoize(timeout=50)
def getuserdata(userid):
    time.sleep(3)
    q = db.session.query(User, Bucket, Card).filter(User.id == Bucket.userid,
                                                    Bucket.id == Card.bucketid,
                                                    User.id == userid)
    df = pd.read_sql_query(q.statement, con=db.engine)
    df.drop('password', axis=1, inplace=True)
    df['dlpassed'] = (df.deadline < pd.Timestamp('today').normalize()) & (df.iscompleted==0)
    return df

@jwt_required()
def create_csv(data = None, listid = None):
    current_userid = get_jwt_identity()
    df = getuserdata(current_userid)
    df = df.assign(
    deadline = lambda x: x['deadline'].dt.strftime('%B %d, %Y'),
    completeddate = lambda x: x['completeddate'].dt.strftime('%B %d, %Y, %r'),
    insertdate = lambda x: x['insertdate'].dt.strftime('%B %d, %Y, %r'),
    updatedate = lambda x: x['updatedate'].dt.strftime('%B %d, %Y, %r')
                )
        
    if (data == 'lists'):
        df =((df.groupby(['bucketname'])[['cardtitle', 'iscompleted']]
             .agg({'cardtitle':'count', 'iscompleted': 'sum'})).reset_index()
                .rename(columns={'cardtitle':'No of Cards', 'iscompleted':'No of Completed'}))
        df.to_csv('static/listsdata.csv', index=False)
    if (data == 'singlelist'):
        df = df.loc[df['id_1']==1][['bucketname', 'cardtitle', 'content',
       'deadline', 'iscompleted', 'completeddate', 'insertdate', 'updatedate',
       'dlpassed']]
        df.to_csv('static/singlelistdata.csv', index=False)
    else:
        df.to_csv('static/userdata.csv', index=False)



class SummaryApi(Resource):
    # @cache.cached(timeout=30)
    @jwt_required()
    def get(self):
        current_userid = get_jwt_identity()
        df = getuserdata(current_userid)
        # df['dlpassed'] = (df.deadline < pd.Timestamp('today').normalize()) & (df.iscompleted==0)
        #print(url_for('static', filename = 'check.png'))
        plt.figure(figsize=(6,4))
        df.groupby('bucketname')['cardtitle'].count().plot.pie(
            #title = 'Your total work load', 
            autopct="%.1f%%", 
            cmap = 'tab20')
        plt.ylabel(None)
        plt.title('Your total work load', y=-0.2)
        #plt.bar(df['iscompleted'].value_counts().index, df['iscompleted'].value_counts())
        plt.tight_layout()
        plt.savefig('static/images/workload.png')
        plt.close()
        
        plt.figure(figsize=(12,8))
        ax = df.groupby(['bucketname', 'iscompleted'])['cardtitle'].count().unstack().rename(columns={0:'Pending', 1:'Completed'}).plot.bar(
            # title = 'Your lists indicating the proportions of \n completed and pending tasks', 
            cmap = 'tab20',rot=45,)
        for container in ax.containers:
            ax.bar_label(container)
        plt.ylabel(None)
        plt.xlabel(None)
        plt.yticks([]) 
        plt.legend(title='--Status--')
        plt.title('Statuses of tasks/cards in each List')
        plt.tight_layout()
        #plt.bar(df['bucketname'].value_counts().index, df['bucketname'].value_counts())
        plt.savefig('static/images/liststatus.png')
        plt.close()
        
        plt.figure(figsize=(20,8))
        completeddaysbeforedeadline = (
        df[df['iscompleted']==1][['cardtitle','deadline','completeddate', 'insertdate']]
        .assign(completeddaysbeforedeadline = lambda x: (x['deadline']-x['completeddate']).dt.days)
        [['cardtitle', 'completeddaysbeforedeadline']]
        .sort_values('completeddaysbeforedeadline', ascending = False)
        # .plot.bar(x= 'cardtitle', y='completeddaysbeforedeadline')

        )
        sns.set(rc={'figure.figsize':(10,8)})
        sns.barplot(data= completeddaysbeforedeadline, 
                    x= 'cardtitle',
                    y='completeddaysbeforedeadline',
                    palette = 'coolwarm', errorbar=None)
        plt.xticks(rotation=45)
        plt.xlabel('Task', fontdict={'fontsize': 16})
        plt.ylabel('Completed days before deadline', fontdict={'fontsize': 16})
        plt.title('Task/Card completion performance', fontdict={'fontsize': 24})
        plt.tight_layout()
        plt.savefig('static/images/perfomance.png')
        plt.close()
        
        images = {
            'lists': '/static/images/liststatus.png',
            'performance': '/static/images/perfomance.png',
            'workload': '/static/images/workload.png',
            'totaltasks': df.shape[0],
            'completedtasks': int(df.iscompleted.sum()),
            'pendingtasks': int((df['iscompleted']==0).sum()),
            'dlpassed': int(df['dlpassed'].sum())
        }
        return jsonify(images)
        
        
        
class UserData(Resource):
    # @cache.cached(timeout=50)
    @jwt_required()
    def get(self):
        current_userid = get_jwt_identity()
        df = getuserdata(current_userid)
        df = df.assign(
        deadline = lambda x: x['deadline'].dt.strftime('%B %d, %Y'),
        completeddate = lambda x: x['completeddate'].dt.strftime('%B %d, %Y, %r'),
        insertdate = lambda x: x['insertdate'].dt.strftime('%B %d, %Y, %r'),
        updatedate = lambda x: x['updatedate'].dt.strftime('%B %d, %Y, %r')
                )
        res = df.to_json(orient="records")
        parsed = json.loads(res)
        return parsed
    
class SendEmail(Resource):
# @cache.cached(timeout=50)
    @jwt_required()
    def get(self):
        current_userid = get_jwt_identity()
        date = datetime.now()
        prev_first = (d.datetime.today().replace(day=1) - d.timedelta(days=1)).replace(day=1)
        prev_last = d.date.today().replace(day=1) - d.timedelta(days=1)
        last_month = format(d.date.today().replace(day=1) - d.timedelta(days=1), '%B %Y')
        # user = User.query.get(current_userid)
        users = User.query.all()
        print(users)
        for user in users:
            df = getuserdata(user.id)
            df = df.loc[(df['completeddate'] >= prev_first)]
            with open('templates/monthlyemail.html') as file_:
                template = Template(file_.read())
                message= template.render(user= user, df = df, date = date, lm = last_month, prev_first= prev_first, prev_last= prev_last)
            msg = MIMEMultipart()
            msg['From'] = SENDER_ADDRESS
            msg['To'] = user.email
            msg['Subject'] = 'Your monthly performance Report'
            msg.attach(MIMEText(message, 'html'))
            
            s = smtplib.SMTP(host = SMPTP_SERVER_HOST, port=SMPTP_SERVER_PORT)
            s.login(SENDER_ADDRESS, SENDER_PASSWORD)
            s.send_message(msg)
            s.quit()
        return True
        
        # msg = Message("Hello",
        #         sender="ganesh@email.com",
        #         recipients=["ganesh@email.com"])
        # msg.html = "<b>testing</b>"
        # mail.send(msg)
    
    

class DataExport(Resource):
    # @cache.cached(timeout=50)
    @jwt_required()
    def get(self):
        time.sleep(5)
        create_csv()
        return send_file(
            'static/userdata.csv',
            mimetype='text/csv',
            download_name='userdata.csv',
            as_attachment=True)
        
class ListsExport(Resource):
    # @cache.cached(timeout=50)
    @jwt_required()
    def get(self):
        time.sleep(5)
        create_csv(data = 'lists')
        return send_file(
            'static/listsdata.csv',
            mimetype='text/csv',
            download_name='userlistsdata.csv',
            as_attachment=True)
        
class CardsExport(Resource):
    # @cache.cached(timeout=50)
    @jwt_required()
    def get(self, bucketid):
        time.sleep(5)
        create_csv(data='singlelist', listid = bucketid)
        return send_file(
            'static/singlelistdata.csv',
            mimetype='text/csv',
            download_name='userlistdata.csv',
            as_attachment=True)