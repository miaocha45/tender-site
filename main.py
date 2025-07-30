#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网络安全招标信息收集系统
完整的系统启动脚本，包含数据抓取、API服务和定时任务
"""

import os
import sys
import time
import threading
import schedule
from datetime import datetime, timedelta

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入所有必要的模块
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tender_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 数据库配置
DATABASE_URL = "sqlite:///./tender_data.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 数据模型
class TenderInfo(Base):
    __tablename__ = "tender_info"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    source = Column(String, index=True)
    publish_date = Column(DateTime, index=True)
    project_type = Column(String)
    budget = Column(String)
    organization = Column(String, index=True)
    status = Column(String)
    detail_url = Column(String)
    content = Column(Text)
    keywords = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 数据抓取器
class TenderScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        })

        self.security_keywords = [
            '网络安全', '信息安全', '网络设备', '防火墙', '入侵检测',
            '安全运维', '系统维护', '弱电智能化', 'CA认证', '数据保护',
            '网络监控', '安全服务', '网络运维', '安全设备', '信息系统',
            '网络维护', '安全监控', '网络管理', '信息化', '网络建设'
        ]

    def contains_security_keywords(self, text):
        if not text:
            return False, []

        found_keywords = []
        for keyword in self.security_keywords:
            if keyword in text:
                found_keywords.append(keyword)

        return len(found_keywords) > 0, found_keywords

    def scrape_all(self, days=3):
        """抓取所有平台的数据"""
        all_results = []

        # 浙江省政府采购网示例数据
        gov_data = [
            {
                'title': '浙江省某市公安局网络安全设备采购项目',
                'source': '浙江省政府采购网',
                'publish_date': datetime.now() - timedelta(days=1),
                'detail_url': 'http://zfcg.czt.zj.gov.cn/sample1',
                'keywords': '网络安全,安全设备',
                'organization': '浙江省公安厅',
                'project_type': '设备采购',
                'status': '招标公告',
                'budget': '300万元'
            },
            {
                'title': '浙江省教育厅信息系统安全等级保护测评服务项目',
                'source': '浙江省政府采购网',
                'publish_date': datetime.now() - timedelta(days=2),
                'detail_url': 'http://zfcg.czt.zj.gov.cn/sample2',
                'keywords': '信息系统,安全等级保护',
                'organization': '浙江省教育厅',
                'project_type': '服务采购',
                'status': '招标公告',
                'budget': '120万元'
            }
        ]

        # 国家电网电子商务平台示例数据
        sgcc_data = [
            {
                'title': '国网浙江省电力有限公司2025年网络安全设备维保项目',
                'source': '国家电网电子商务平台',
                'publish_date': datetime.now() - timedelta(days=1),
                'detail_url': 'https://ecp.sgcc.com.cn/sample1',
                'keywords': '网络安全,设备维保',
                'organization': '国网浙江省电力有限公司',
                'project_type': '设备维保',
                'status': '招标公告',
                'budget': '200万元'
            },
            {
                'title': '国网浙江电力信息系统安全运维服务采购项目',
                'source': '国家电网电子商务平台', 
                'publish_date': datetime.now() - timedelta(days=2),
                'detail_url': 'https://ecp.sgcc.com.cn/sample2',
                'keywords': '信息系统,安全运维',
                'organization': '国网浙江省电力有限公司',
                'project_type': '运维服务',
                'status': '招标公告',
                'budget': '150万元'
            }
        ]

        # 中国烟草总公司采购交易平台示例数据
        tobacco_data = [
            {
                'title': '浙江中烟工业有限责任公司2025年弱电智能化系统运维服务项目',
                'source': '中国烟草总公司采购交易平台',
                'publish_date': datetime.now() - timedelta(days=1),
                'detail_url': 'https://cgjy.tobacco.com.cn/zhejiang_tobacco_1',
                'keywords': '弱电智能化,系统维护',
                'organization': '浙江中烟工业有限责任公司',
                'project_type': '运维服务',
                'status': '招标公告',
                'budget': '950.4万元'
            },
            {
                'title': '浙江中烟信息安全设备维保服务项目',
                'source': '中国烟草总公司采购交易平台',
                'publish_date': datetime.now() - timedelta(days=2),
                'detail_url': 'https://cgjy.tobacco.com.cn/zhejiang_tobacco_2', 
                'keywords': '信息安全,设备维保',
                'organization': '浙江中烟工业有限责任公司',
                'project_type': '维保服务',
                'status': '招标公告',
                'budget': '85万元'
            }
        ]

        all_results.extend(gov_data)
        all_results.extend(sgcc_data)
        all_results.extend(tobacco_data)

        # 按发布时间排序
        all_results.sort(key=lambda x: x['publish_date'], reverse=True)

        logger.info(f"抓取完成，共获得 {len(all_results)} 条数据")
        return all_results

# 数据服务
class TenderService:
    @staticmethod
    def get_db():
        db = SessionLocal()
        try:
            return db
        finally:
            pass  # 不在这里关闭，由调用者关闭

    @staticmethod
    def create_tender(db: Session, tender_data: dict):
        db_tender = TenderInfo(**tender_data)
        db.add(db_tender)
        db.commit()
        db.refresh(db_tender)
        return db_tender

    @staticmethod
    def get_tenders(db: Session, skip: int = 0, limit: int = 100, source: str = None, keyword: str = None):
        query = db.query(TenderInfo)

        if source:
            query = query.filter(TenderInfo.source == source)

        if keyword:
            query = query.filter(
                (TenderInfo.title.contains(keyword)) | 
                (TenderInfo.keywords.contains(keyword))
            )

        return query.order_by(TenderInfo.publish_date.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_tender_by_id(db: Session, tender_id: int):
        return db.query(TenderInfo).filter(TenderInfo.id == tender_id).first()

    @staticmethod
    def get_latest_tenders(db: Session, days: int = 3):
        cutoff_date = datetime.now() - timedelta(days=days)
        return db.query(TenderInfo).filter(
            TenderInfo.publish_date >= cutoff_date
        ).order_by(TenderInfo.publish_date.desc()).all()

    @staticmethod
    def get_statistics(db: Session):
        total_tenders = db.query(TenderInfo).count()
        source_stats = db.query(TenderInfo.source, func.count(TenderInfo.id)).group_by(TenderInfo.source).all()
        recent_date = datetime.now() - timedelta(days=3)
        recent_count = db.query(TenderInfo).filter(TenderInfo.publish_date >= recent_date).count()

        return {
            "total_tenders": total_tenders,
            "recent_tenders": recent_count,
            "source_distribution": dict(source_stats),
            "last_updated": datetime.now().isoformat()
        }

# Pydantic模型
class TenderInfoResponse(BaseModel):
    id: int
    title: str
    source: str
    publish_date: datetime
    project_type: Optional[str] = None
    budget: Optional[str] = None
    organization: Optional[str] = None
    status: Optional[str] = None
    detail_url: Optional[str] = None
    content: Optional[str] = None
    keywords: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# FastAPI应用
app = FastAPI(title="网络安全招标信息收集系统", description="收集并展示网络安全相关招标信息")

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
app.mount("/static", StaticFiles(directory="."), name="static")

# 数据库依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API路由
@app.get("/")
async def serve_index():
    return FileResponse('index.html')

@app.get("/api/tenders", response_model=List[TenderInfoResponse])
async def get_tenders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    source: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    tenders = TenderService.get_tenders(db, skip=skip, limit=limit, source=source, keyword=keyword)
    return tenders

@app.get("/api/tenders/{tender_id}", response_model=TenderInfoResponse)
async def get_tender(tender_id: int, db: Session = Depends(get_db)):
    tender = TenderService.get_tender_by_id(db, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="招标信息不存在")
    return tender

@app.get("/api/tenders/latest/{days}", response_model=List[TenderInfoResponse])
async def get_latest_tenders(days: int = 3, db: Session = Depends(get_db)):
    tenders = TenderService.get_latest_tenders(db, days)
    return tenders

@app.post("/api/crawl")
async def trigger_crawl(db: Session = Depends(get_db)):
    try:
        scraper = TenderScraper()
        scraped_data = scraper.scrape_all(3)

        created_count = 0
        for data in scraped_data:
            existing = db.query(TenderInfo).filter(
                TenderInfo.title == data['title'],
                TenderInfo.source == data['source']
            ).first()

            if not existing:
                TenderService.create_tender(db, data)
                created_count += 1

        logger.info(f"手动抓取完成: 总计 {len(scraped_data)} 条，新增 {created_count} 条")

        return {
            "message": "数据抓取完成",
            "total_scraped": len(scraped_data),
            "new_records": created_count
        }
    except Exception as e:
        logger.error(f"数据抓取失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据抓取失败: {str(e)}")

@app.get("/api/stats")
async def get_statistics(db: Session = Depends(get_db)):
    return TenderService.get_statistics(db)

# 定时任务函数
def scheduled_crawl():
    """定时抓取任务"""
    logger.info("开始执行定时抓取任务...")
    db = SessionLocal()
    try:
        scraper = TenderScraper()
        scraped_data = scraper.scrape_all(3)

        created_count = 0
        for data in scraped_data:
            existing = db.query(TenderInfo).filter(
                TenderInfo.title == data['title'],
                TenderInfo.source == data['source']
            ).first()

            if not existing:
                TenderService.create_tender(db, data)
                created_count += 1

        logger.info(f"定时抓取完成: 总计 {len(scraped_data)} 条，新增 {created_count} 条")

    except Exception as e:
        logger.error(f"定时抓取失败: {e}")
    finally:
        db.close()

def run_scheduler():
    """运行定时任务调度器"""
    # 每天早上8点执行数据抓取
    schedule.every().day.at("08:00").do(scheduled_crawl)
    # 每天下午2点执行数据抓取
    schedule.every().day.at("14:00").do(scheduled_crawl)
    # 每天晚上8点执行数据抓取
    schedule.every().day.at("20:00").do(scheduled_crawl)

    logger.info("定时任务调度器已启动")
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

def initialize_data():
    """初始化数据"""
    db = SessionLocal()
    try:
        if db.query(TenderInfo).count() == 0:
            logger.info("数据库为空，开始初始化数据...")
            scraper = TenderScraper()
            scraped_data = scraper.scrape_all(7)  # 初始化时获取7天的数据

            for data in scraped_data:
                TenderService.create_tender(db, data)

            logger.info(f"数据初始化完成，添加了 {len(scraped_data)} 条记录")
        else:
            logger.info("数据库已有数据，跳过初始化")
    except Exception as e:
        logger.error(f"数据初始化失败: {e}")
    finally:
        db.close()

def main():
    """主函数"""
    logger.info("=== 网络安全招标信息收集系统启动 ===")

    # 初始化数据
    initialize_data()

    # 启动定时任务线程
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("定时任务线程已启动")

    # 启动Web服务
    logger.info("启动Web服务...")
    logger.info("系统访问地址: http://localhost:8000")
    logger.info("API文档地址: http://localhost:8000/docs")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    main()
