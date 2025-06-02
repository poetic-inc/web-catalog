from typing import List

from pydantic import BaseModel


class Item(BaseModel):
    name: str
    price: str


class Product(BaseModel):
    category: str
    items: List[Item]


class Page(BaseModel):
    name: str
    url: str


class ProductModel(BaseModel):
    page_url: str
    products: List[Product]
