import os, uuid, datetime as dt
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import create_engine, String, Integer, Date, DateTime, ForeignKey, Text, Numeric, Boolean, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, sessionmaker
from pydantic import BaseModel, EmailStr, ConfigDict
from passlib.context import CryptContext
from jose import jwt, JWTError

DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///./apcontrol.db')
JWT_SECRET=os.getenv('JWT_SECRET','dev-secret-change-me')
ALGO='HS256'
engine=create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass

def uid(): return str(uuid.uuid4())

class Company(Base):
    __tablename__='companies'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    name: Mapped[str]=mapped_column(String(200))
    created_at: Mapped[dt.datetime]=mapped_column(DateTime,default=dt.datetime.utcnow)

class User(Base):
    __tablename__='users'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    company_id: Mapped[str]=mapped_column(ForeignKey('companies.id'))
    email: Mapped[str]=mapped_column(String(255),unique=True,index=True)
    password_hash: Mapped[str]=mapped_column(String(255))
    full_name: Mapped[str]=mapped_column(String(200))
    role: Mapped[str]=mapped_column(String(60),default='owner')
    is_active: Mapped[bool]=mapped_column(Boolean,default=True)

class Project(Base):
    __tablename__='projects'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    company_id: Mapped[str]=mapped_column(ForeignKey('companies.id'),index=True)
    name: Mapped[str]=mapped_column(String(220))
    type: Mapped[str]=mapped_column(String(80),default='Строительство')
    status: Mapped[str]=mapped_column(String(80),default='Подготовка')
    address: Mapped[Optional[str]]=mapped_column(String(400),nullable=True)
    start: Mapped[Optional[dt.date]]=mapped_column(Date,nullable=True)
    end: Mapped[Optional[dt.date]]=mapped_column(Date,nullable=True)
    description: Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    created_at: Mapped[dt.datetime]=mapped_column(DateTime,default=dt.datetime.utcnow)

class Stage(Base):
    __tablename__='stages'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    company_id: Mapped[str]=mapped_column(ForeignKey('companies.id'),index=True)
    project_id: Mapped[str]=mapped_column(ForeignKey('projects.id'),index=True)
    parent_id: Mapped[Optional[str]]=mapped_column(ForeignKey('stages.id'),nullable=True)
    name: Mapped[str]=mapped_column(String(220))
    status: Mapped[str]=mapped_column(String(80),default='Не начат')
    start: Mapped[Optional[dt.date]]=mapped_column(Date,nullable=True)
    end: Mapped[Optional[dt.date]]=mapped_column(Date,nullable=True)
    responsible: Mapped[Optional[str]]=mapped_column(String(220),nullable=True)
    checker: Mapped[Optional[str]]=mapped_column(String(220),nullable=True)
    cost: Mapped[Optional[float]]=mapped_column(Numeric(14,2),nullable=True)
    progress: Mapped[int]=mapped_column(Integer,default=0)

class Task(Base):
    __tablename__='tasks'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    company_id: Mapped[str]=mapped_column(ForeignKey('companies.id'),index=True)
    project_id: Mapped[Optional[str]]=mapped_column(ForeignKey('projects.id'),nullable=True,index=True)
    stage_id: Mapped[Optional[str]]=mapped_column(ForeignKey('stages.id'),nullable=True,index=True)
    name: Mapped[str]=mapped_column(String(260))
    description: Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    executor: Mapped[Optional[str]]=mapped_column(String(220),nullable=True)
    due: Mapped[Optional[dt.date]]=mapped_column(Date,nullable=True)
    priority: Mapped[str]=mapped_column(String(40),default='Обычный')
    status: Mapped[str]=mapped_column(String(60),default='Активная')
    created_at: Mapped[dt.datetime]=mapped_column(DateTime,default=dt.datetime.utcnow)

class Employee(Base):
    __tablename__='employees'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    company_id: Mapped[str]=mapped_column(ForeignKey('companies.id'),index=True)
    name: Mapped[str]=mapped_column(String(220))
    job: Mapped[Optional[str]]=mapped_column(String(160),nullable=True)
    role: Mapped[str]=mapped_column(String(80),default='Работник')
    phone: Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
    email: Mapped[Optional[str]]=mapped_column(String(255),nullable=True)
    telegram: Mapped[Optional[str]]=mapped_column(String(120),nullable=True)
    hire_date: Mapped[Optional[dt.date]]=mapped_column(Date,nullable=True)
    status: Mapped[str]=mapped_column(String(80),default='Ожидает активации')

class Client(Base):
    __tablename__='clients'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    company_id: Mapped[str]=mapped_column(ForeignKey('companies.id'),index=True)
    name: Mapped[str]=mapped_column(String(220))
    phone: Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
    email: Mapped[Optional[str]]=mapped_column(String(255),nullable=True)
    whatsapp: Mapped[Optional[str]]=mapped_column(String(120),nullable=True)
    telegram: Mapped[Optional[str]]=mapped_column(String(120),nullable=True)
    status: Mapped[str]=mapped_column(String(60),default='Активный')

class Tool(Base):
    __tablename__='tools'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    company_id: Mapped[str]=mapped_column(ForeignKey('companies.id'),index=True)
    name: Mapped[str]=mapped_column(String(220))
    inventory_no: Mapped[Optional[str]]=mapped_column(String(120),nullable=True)
    cost: Mapped[Optional[float]]=mapped_column(Numeric(14,2),nullable=True)
    status: Mapped[str]=mapped_column(String(60),default='Склад')
    responsible: Mapped[Optional[str]]=mapped_column(String(220),nullable=True)

class Camera(Base):
    __tablename__='cameras'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    company_id: Mapped[str]=mapped_column(ForeignKey('companies.id'),index=True)
    project_id: Mapped[Optional[str]]=mapped_column(ForeignKey('projects.id'),nullable=True)
    name: Mapped[str]=mapped_column(String(220))
    type: Mapped[str]=mapped_column(String(100),default='RTSP / ONVIF')
    url: Mapped[Optional[str]]=mapped_column(String(800),nullable=True)
    status: Mapped[str]=mapped_column(String(80),default='Не подключена')

class Finance(Base):
    __tablename__='finance'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    company_id: Mapped[str]=mapped_column(ForeignKey('companies.id'),index=True)
    project_id: Mapped[Optional[str]]=mapped_column(ForeignKey('projects.id'),nullable=True)
    type: Mapped[str]=mapped_column(String(80))
    category: Mapped[Optional[str]]=mapped_column(String(120),nullable=True)
    amount: Mapped[float]=mapped_column(Numeric(14,2))
    comment: Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    created_at: Mapped[dt.datetime]=mapped_column(DateTime,default=dt.datetime.utcnow)

class Activity(Base):
    __tablename__='activity'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    company_id: Mapped[str]=mapped_column(ForeignKey('companies.id'),index=True)
    user_id: Mapped[Optional[str]]=mapped_column(ForeignKey('users.id'),nullable=True)
    entity_type: Mapped[str]=mapped_column(String(80))
    entity_id: Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
    action: Mapped[str]=mapped_column(String(120))
    details: Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    created_at: Mapped[dt.datetime]=mapped_column(DateTime,default=dt.datetime.utcnow)

class StoredFile(Base):
    __tablename__='files'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    company_id: Mapped[str]=mapped_column(ForeignKey('companies.id'),index=True)
    project_id: Mapped[Optional[str]]=mapped_column(ForeignKey('projects.id'),nullable=True)
    filename: Mapped[str]=mapped_column(String(500))
    path: Mapped[str]=mapped_column(String(800))
    uploaded_at: Mapped[dt.datetime]=mapped_column(DateTime,default=dt.datetime.utcnow)

Base.metadata.create_all(engine)

pwd=CryptContext(schemes=['bcrypt'],deprecated='auto')
oauth=OAuth2PasswordBearer(tokenUrl='/api/auth/login')

def dbs():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def token_for(u:User):
    exp=dt.datetime.utcnow()+dt.timedelta(hours=12)
    return jwt.encode({'sub':u.id,'company_id':u.company_id,'role':u.role,'exp':exp},JWT_SECRET,algorithm=ALGO)

def current_user(token:str=Depends(oauth),db:Session=Depends(dbs)):
    try: payload=jwt.decode(token,JWT_SECRET,algorithms=[ALGO]); uid=payload.get('sub')
    except JWTError: raise HTTPException(401,'Недействительная сессия')
    u=db.get(User,uid)
    if not u or not u.is_active: raise HTTPException(401,'Пользователь недоступен')
    return u

def log(db,u,etype,eid,action,details=None):
    db.add(Activity(company_id=u.company_id,user_id=u.id,entity_type=etype,entity_id=eid,action=action,details=details))

class RegisterIn(BaseModel):
    company_name:str; full_name:str; email:EmailStr; password:str
class LoginIn(BaseModel): email:EmailStr; password:str
class ProjectIn(BaseModel):
    name:str; type:str='Строительство'; status:str='Подготовка'; address:Optional[str]=None; start:Optional[dt.date]=None; end:Optional[dt.date]=None; description:Optional[str]=None
class StageIn(BaseModel):
    name:str; status:str='Не начат'; start:Optional[dt.date]=None; end:Optional[dt.date]=None; responsible:Optional[str]=None; checker:Optional[str]=None; cost:Optional[float]=None; progress:int=0; parent_id:Optional[str]=None
class TaskIn(BaseModel):
    name:str; project_id:Optional[str]=None; stage_id:Optional[str]=None; description:Optional[str]=None; executor:Optional[str]=None; due:Optional[dt.date]=None; priority:str='Обычный'; status:str='Активная'
class EmployeeIn(BaseModel):
    name:str; job:Optional[str]=None; role:str='Работник'; phone:Optional[str]=None; email:Optional[str]=None; telegram:Optional[str]=None; hire_date:Optional[dt.date]=None; status:str='Ожидает активации'
class ClientIn(BaseModel):
    name:str; phone:Optional[str]=None; email:Optional[str]=None; whatsapp:Optional[str]=None; telegram:Optional[str]=None; status:str='Активный'
class ToolIn(BaseModel):
    name:str; inventory_no:Optional[str]=None; cost:Optional[float]=None; status:str='Склад'; responsible:Optional[str]=None
class CameraIn(BaseModel):
    name:str; project_id:Optional[str]=None; type:str='RTSP / ONVIF'; url:Optional[str]=None; status:str='Не подключена'
class FinanceIn(BaseModel):
    project_id:Optional[str]=None; type:str; category:Optional[str]=None; amount:float; comment:Optional[str]=None

def serialize(obj):
    d={}
    for c in obj.__table__.columns:
        v=getattr(obj,c.name)
        if isinstance(v,(dt.date,dt.datetime)): v=v.isoformat()
        elif hasattr(v,'__float__') and not isinstance(v,(str,int,float,bool,type(None))):
            try:v=float(v)
            except:pass
        d[c.name]=v
    return d

app=FastAPI(title='ALI Project Control API',version='0.3')
origins=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:8080').split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])

@app.get('/api/health')
def health(): return {'ok':True,'version':'0.3'}

@app.post('/api/auth/register')
def register(x:RegisterIn,db:Session=Depends(dbs)):
    if db.scalar(select(User).where(User.email==x.email)): raise HTTPException(409,'Email уже зарегистрирован')
    c=Company(name=x.company_name);db.add(c);db.flush()
    u=User(company_id=c.id,email=x.email,password_hash=pwd.hash(x.password),full_name=x.full_name,role='owner')
    db.add(u);db.commit();db.refresh(u)
    return {'token':token_for(u),'user':serialize(u),'company':serialize(c)}

@app.post('/api/auth/login')
def login(x:LoginIn,db:Session=Depends(dbs)):
    u=db.scalar(select(User).where(User.email==x.email))
    if not u or not pwd.verify(x.password,u.password_hash): raise HTTPException(401,'Неверный email или пароль')
    return {'token':token_for(u),'user':serialize(u)}

@app.get('/api/me')
def me(u:User=Depends(current_user),db:Session=Depends(dbs)):
    c=db.get(Company,u.company_id)
    return {'user':serialize(u),'company':serialize(c)}

# Generic helpers
MODELS={'projects':Project,'tasks':Task,'employees':Employee,'clients':Client,'tools':Tool,'cameras':Camera,'finance':Finance}
SCHEMAS={'projects':ProjectIn,'tasks':TaskIn,'employees':EmployeeIn,'clients':ClientIn,'tools':ToolIn,'cameras':CameraIn,'finance':FinanceIn}

@app.get('/api/bootstrap')
def bootstrap(u:User=Depends(current_user),db:Session=Depends(dbs)):
    data={}
    for name,model in MODELS.items():
        rows=db.scalars(select(model).where(model.company_id==u.company_id).order_by(model.__table__.c.id)).all()
        data[name]=[serialize(r) for r in rows]
    stages=db.scalars(select(Stage).where(Stage.company_id==u.company_id)).all()
    data['stages']=[serialize(s) for s in stages]
    acts=db.scalars(select(Activity).where(Activity.company_id==u.company_id).order_by(Activity.created_at.desc()).limit(30)).all()
    data['activity']=[serialize(a) for a in acts]
    return data

@app.post('/api/projects')
def create_project(x:ProjectIn,u:User=Depends(current_user),db:Session=Depends(dbs)):
    o=Project(company_id=u.company_id,**x.model_dump());db.add(o);db.flush();log(db,u,'project',o.id,'created',o.name);db.commit();db.refresh(o);return serialize(o)
@app.post('/api/projects/{pid}/stages')
def create_stage(pid:str,x:StageIn,u:User=Depends(current_user),db:Session=Depends(dbs)):
    p=db.get(Project,pid)
    if not p or p.company_id!=u.company_id: raise HTTPException(404,'Объект не найден')
    o=Stage(company_id=u.company_id,project_id=pid,**x.model_dump());db.add(o);db.flush();log(db,u,'stage',o.id,'created',o.name);db.commit();db.refresh(o);return serialize(o)

@app.post('/api/{kind}')
def create_generic(kind:str,payload:dict,u:User=Depends(current_user),db:Session=Depends(dbs)):
    if kind not in MODELS or kind=='projects': raise HTTPException(404,'Неизвестный раздел')
    schema=SCHEMAS[kind]
    try:x=schema(**payload)
    except Exception as e: raise HTTPException(422,str(e))
    model=MODELS[kind]; o=model(company_id=u.company_id,**x.model_dump());db.add(o);db.flush();log(db,u,kind[:-1] if kind.endswith('s') else kind,o.id,'created',getattr(o,'name',None) or getattr(o,'type',kind));db.commit();db.refresh(o);return serialize(o)

@app.patch('/api/tasks/{tid}/status')
def task_status(tid:str,status:str,u:User=Depends(current_user),db:Session=Depends(dbs)):
    t=db.get(Task,tid)
    if not t or t.company_id!=u.company_id: raise HTTPException(404,'Задача не найдена')
    old=t.status;t.status=status;log(db,u,'task',t.id,'status_changed',f'{old} -> {status}');db.commit();return serialize(t)

@app.get('/api/activity')
def activity(u:User=Depends(current_user),db:Session=Depends(dbs)):
    rows=db.scalars(select(Activity).where(Activity.company_id==u.company_id).order_by(Activity.created_at.desc()).limit(100)).all()
    return [serialize(r) for r in rows]

@app.post('/api/files')
def upload_file(project_id:Optional[str]=None,file:UploadFile=File(...),u:User=Depends(current_user),db:Session=Depends(dbs)):
    os.makedirs('/app/uploads',exist_ok=True)
    safe=f'{uid()}_{os.path.basename(file.filename)}'; path=f'/app/uploads/{safe}'
    with open(path,'wb') as out:
        while chunk:=file.file.read(1024*1024): out.write(chunk)
    sf=StoredFile(company_id=u.company_id,project_id=project_id,filename=file.filename,path=path);db.add(sf);db.flush();log(db,u,'file',sf.id,'uploaded',file.filename);db.commit();db.refresh(sf)
    return serialize(sf)
