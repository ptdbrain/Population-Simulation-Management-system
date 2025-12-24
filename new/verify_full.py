
# Verification Script for Residence Management System
# Usage: python verify_full.py
# (Ensure server is running: uvicorn app.main:app)
# Note: This script uses httpx to call APIs.

import asyncio
import httpx
from datetime import date, timedelta

BASE_URL = "http://localhost:8000"

async def test_flow():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        print("1. Login as Admin...")
        resp = await client.post("/token", data={"username": "admin", "password": "admin123"})
        if resp.status_code != 200:
            print("Login failed:", resp.text)
            return
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login success.")

        print("\n2. Create Household...")
        hh_data = {
            "household_code": "TEST-001",
            "owner_id": 1, # Use existing resident from seed
            "address": "Test Street 1"
        }
        resp = await client.post("/households/", json=hh_data, headers=headers)
        if resp.status_code == 200:
            print("Create Household: Success", resp.json())
            hh_id = resp.json()["id"]
        else:
            print("Create Household Failed:", resp.text)
            # Try to fetch if exists
            hh_id = 3 # Guess

        print("\n3. Add Person (Resident)...")
        p_data = {
            "full_name": "Test Resident",
            "dob": "2000-01-01",
            "gender": "MALE",
            "cid": "999999999999",
            "relation_to_owner": "MEMBER",
            "household_id": hh_id
        }
        resp = await client.post("/persons/", json=p_data, headers=headers)
        if resp.status_code == 200:
            print("Create Person: Success", resp.json())
        else:
            print("Create Person Failed:", resp.text)

        print("\n4. Temp Residence Registration...")
        tr_data = {
            "full_name": "Visitor A",
            "dob": "1990-01-01",
            "origin_address": "Far Away",
            "host_household_id": hh_id,
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=7)),
            "reason": "Visiting"
        }
        resp = await client.post("/temp-residences", json=tr_data, headers=headers)
        if resp.status_code == 200:
            tr_id = resp.json()["id"]
            print("Register Temp: Success", tr_id)
            
            # Approve
            resp_app = await client.post(f"/temp-residences/{tr_id}/approve", headers=headers)
            print("Approve Temp:", resp_app.json())
        else:
            print("Register Temp Failed:", resp.text)

        print("\n5. Complaint & Status...")
        c_data = {"content": "Noise complaint", "category": "SECURITY"}
        resp = await client.post("/complaints/", json=c_data, headers=headers)
        if resp.status_code == 200:
            c_id = resp.json().get("complaint_id", resp.json().get("id"))
            print("Complaint Created:", c_id)
            
            # Update status
            status_data = {"status": "RESOLVED", "resolution_note": "Talked to neighbor"}
            resp_up = await client.put(f"/complaints/{c_id}/status?status=RESOLVED&resolution_note=Done", headers=headers)
            print("Update Status:", resp_up.json())
        else:
            print("Complaint Failed:", resp.text)

if __name__ == "__main__":
    try:
        asyncio.run(test_flow())
    except Exception as e:
        print("Error:", e)
        print("Make sure server is running on port 8000")
