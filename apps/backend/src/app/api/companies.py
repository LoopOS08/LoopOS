from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.company import Company

router = APIRouter()


class CompanyCreate(BaseModel):
    name: str
    settings: Optional[dict] = {}


class CompanyResponse(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str
    settings: dict
    
    class Config:
        from_attributes = True


@router.post("/", response_model=CompanyResponse)
async def create_company(
    company: CompanyCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new company"""
    db_company = Company(
        name=company.name,
        settings=company.settings
    )
    db.add(db_company)
    await db.commit()
    await db.refresh(db_company)
    return db_company


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get company by ID"""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return company


@router.get("/", response_model=List[CompanyResponse])
async def list_companies(db: AsyncSession = Depends(get_db)):
    """List all companies"""
    result = await db.execute(select(Company))
    companies = result.scalars().all()
    return companies