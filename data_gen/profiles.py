"""Deterministic synthetic patient/provider profiles (Faker, seeded per case). Pure function of (seed, case_id)."""
import hashlib
import random

from faker import Faker


def profile(seed, case_id):
    h = int(hashlib.sha256(f"{seed}:{case_id}".encode()).hexdigest()[:8], 16)
    fake = Faker("en_US")
    fake.seed_instance(h)
    rng = random.Random(h)
    sex = rng.choice(["F", "M"])
    first = fake.first_name_female() if sex == "F" else fake.first_name_male()
    last = fake.last_name()
    return {
        "name": f"{first} {last}", "last_name": last, "sex": sex,
        "dob": fake.date_of_birth(minimum_age=35, maximum_age=80).isoformat(),
        "address": f"{fake.street_address()}, {fake.city()}, {fake.state_abbr()} {fake.zipcode()}",
        "phone": f"555-01{rng.randint(0, 99):02d}",
        "ssn": f"9{rng.randint(0, 99):02d}-{rng.randint(10, 99)}-{rng.randint(1000, 9999)}",  # 9xx: never issued
        "mrn": f"SYN-{rng.randint(100000, 999999)}",
        "member_id": f"MBR{rng.randint(100000000, 999999999)}",
        "practice": f"{fake.last_name()} Medical Group",
        "provider": f"Dr. {fake.first_name()} {fake.last_name()}",
        "specialist": f"Dr. {fake.first_name()} {fake.last_name()}",
        "therapist": f"{fake.first_name()} {fake.last_name()}, PT",
        "trace": f"SYN-EFT-{rng.randint(10000000, 99999999)}",
    }
