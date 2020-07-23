import yfinance as yf
from fastapi import FastAPI, Request, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import models
from database.db import engine, SessionLocal
from schema.stock_schema import StockRequest
from database.models import Stock

app = FastAPI()

templates = Jinja2Templates(directory="templates")

models.Base.metadata.create_all(bind=engine)


def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def fetch_data(symbol: str):
    data = yf.Ticker(symbol)

    db = SessionLocal()

    stock = Stock()
    stock.symbol = symbol
    stock.dividend_yield = data.info['dividendYield'] * 100
    stock.dividend_rate = data.info['dividendRate'] * 100
    stock.forward_eps = data.info['forwardEps']
    stock.forward_pe = data.info['forwardPE']
    stock.price = data.info['previousClose']
    stock.ma50 = data.info['fiftyDayAverage']
    stock.ma200 = data.info['twoHundredDayAverage']
    stock.peg_ratio = data.info['pegRatio']
    stock.payout_ratio = data.info['payoutRatio']

    db.add(stock)
    db.commit()


@app.get("/")
def home(request: Request,
         dividend_yield=None,
         forward_pe=None,
         ma50=None,
         ma200=None,
         db: Session = Depends(get_db)):
    """
    Displays the stock dash dashboard/homepage
    """
    stock = db.query(Stock)

    if dividend_yield:
        stock = stock.filter(Stock.dividend_yield > dividend_yield)
    if forward_pe:
        stock = stock.filter(Stock.forward_pe < forward_pe)
    if ma50:
        stock = stock.filter(Stock.price > Stock.ma50)
    if ma200:
        stock = stock.filter(Stock.price > Stock.ma200)

    stocks = stock.all()

    return templates.TemplateResponse('index.html',
                                      {"request": request,
                                       "stocks": stocks,
                                       "dividend_yield": dividend_yield,
                                       "forward_pe": forward_pe,
                                       "ma50": ma50,
                                       "ma200": ma200})


@app.post("/stocks")
async def create_stocks(stock_request: StockRequest,
                        background_tasks: BackgroundTasks,
                        ):
    """
    Create a stock and store it in a database
    """
    symbol = stock_request.symbol
    trye = yf.Ticker(symbol)
    try:
        trye.info
    except KeyError:
        result = {'result': 'Symbol doesnt exist'}
        return result

    background_tasks.add_task(fetch_data, symbol)

    return {
        "status_code": 200,
        "message": "Stock created"
    }


@app.get("/stocks/{stocks_id}")
def read_stock(stock_id: int, q: str = None):
    return {"stock_id": stock_id, "q": q}
