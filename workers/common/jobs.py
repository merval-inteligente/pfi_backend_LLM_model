import os, datetime
from pymongo import ReturnDocument

LEASE_MINUTES = int(os.getenv("LEASE_MINUTES", "30"))

def claim_job(db, types=("scrape","ml-train","ml-infer")):
    now = datetime.datetime.utcnow()
    lease_until = now + datetime.timedelta(minutes=LEASE_MINUTES)
    return db["jobs"].find_one_and_update(
        {
            "type": {"$in": list(types)},
            "status": "queued",
            "$or": [{"leaseUntil": None}, {"leaseUntil": {"$lte": now}}],
        },
        {
            "$set": {"status": "running", "leaseUntil": lease_until},
            "$inc": {"attempts": 1}
        },
        sort=[("priority", -1), ("createdAt", 1)],
        return_document=ReturnDocument.AFTER
    )

def complete_job(db, job_id, ok, result=None, error=None):
    jobs = db["jobs"]
    if ok:
        jobs.update_one({"_id": job_id}, {"$set": {"status": "succeeded", "result": result, "leaseUntil": None}})
    else:
        job = jobs.find_one({"_id": job_id})
        if job and job.get("attempts", 0) < job.get("maxAttempts", 3):
            # reencolar
            jobs.update_one({"_id": job_id}, {"$set": {"status": "queued", "leaseUntil": None}})
        else:
            jobs.update_one({"_id": job_id}, {"$set": {"status": "failed", "error": error, "leaseUntil": None}})
