"""Fetch and cache FIRMS area CSV chunks."""
import argparse,asyncio
from datetime import date
from agnivani.config import Settings
from agnivani.ingest.firms import FirmsClient
async def main(days):
    settings=Settings(); paths=await FirmsClient(settings).fetch_range(days,date.today())
    for path in paths:print(path)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--days",type=int,default=5);a=p.parse_args();asyncio.run(main(a.days))
