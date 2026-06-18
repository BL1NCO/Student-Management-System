import os
import json
import uuid
from pathlib import Path
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
from statistics import mean, median, stdev


DATA_DIR = Path.home() / ".student_mgmt"
DATA_FILE = DATA_DIR / "students.json"


class Grade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    C_PLUS = "C+"
    C = "C"
    C_MINUS = "C-"
    D = "D"
    F = "F"


GRADE_POINTS = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D": 1.0, "F": 0.0,
}

SCORE_TO_GRADE = [
    (97, "A+"), (93, "A"), (90, "A-"),
    (87, "B+"), (83, "B"), (80, "B-"),
    (77, "C+"), (73, "C"), (70, "C-"),
    (60, "D"), (0, "F"),
]


def score_to_grade(score: float) -> str:
    for threshold, grade in SCORE_TO_GRADE:
        if score >= threshold:
            return grade
    return "F"


@dataclass
class CourseRecord:
    course_code: str
    course_name: str
    credits: int
    score: float
    semester: str

    @property
    def grade(self) -> str:
        return score_to_grade(self.score)

    @property
    def grade_points(self) -> float:
        return GRADE_POINTS.get(self.grade, 0.0)

    @property
    def weighted_points(self) -> float:
        return self.grade_points * self.credits


@dataclass
class Student:
    id: str
    first_name: str
    last_name: str
    email: str
    date_of_birth: str
    major: str
    year: int
    enrolled: bool
    created_at: str
    updated_at: str
    courses: list[dict] = field(default_factory=list)
    notes: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int:
        birth = datetime.strptime(self.date_of_birth, "%Y-%m-%d").date()
        today = date.today()
        return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

    @property
    def course_records(self) -> list[CourseRecord]:
        return [CourseRecord(**c) for c in self.courses]

    @property
    def gpa(self) -> Optional[float]:
        records = self.course_records
        if not records:
            return None
        total_points = sum(r.weighted_points for r in records)
        total_credits = sum(r.credits for r in records)
        return round(total_points / total_credits, 2) if total_credits else None

    @property
    def total_credits(self) -> int:
        return sum(c["credits"] for c in self.courses)

    @property
    def standing(self) -> str:
        gpa = self.gpa
        if gpa is None:
            return "—"
        if gpa >= 3.7:
            return "Dean's List"
        elif gpa >= 3.0:
            return "Good Standing"
        elif gpa >= 2.0:
            return "Satisfactory"
        return "Academic Probation"


class StudentRepository:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        self._students: dict[str, Student] = {}
        self._load()

    def _load(self):
        if DATA_FILE.exists():
            with open(DATA_FILE) as f:
                raw = json.load(f)
            self._students = {sid: Student(**data) for sid, data in raw.items()}

    def _save(self):
        with open(DATA_FILE, "w") as f:
            serialized = {}
            for sid, student in self._students.items():
                data = asdict(student)
                serialized[sid] = data
            json.dump(serialized, f, indent=2)

    def add(self, student: Student) -> Student:
        self._students[student.id] = student
        self._save()
        return student

    def get(self, student_id: str) -> Optional[Student]:
        return self._students.get(student_id)

    def find_by_email(self, email: str) -> Optional[Student]:
        return next((s for s in self._students.values() if s.email.lower() == email.lower()), None)

    def update(self, student: Student) -> bool:
        if student.id not in self._students:
            return False
        self._students[student.id] = student
        self._save()
        return True

    def delete(self, student_id: str) -> bool:
        if student_id not in self._students:
            return False
        del self._students[student_id]
        self._save()
        return True

    def search(self, query: str) -> list[Student]:
        q = query.lower()
        return [
            s for s in self._students.values()
            if q in s.full_name.lower() or q in s.email.lower()
            or q in s.major.lower() or q in s.id.lower()
        ]

    def all(self) -> list[Student]:
        return sorted(self._students.values(), key=lambda s: s.last_name.lower())

    def filter_by_major(self, major: str) -> list[Student]:
        return [s for s in self._students.values() if s.major.lower() == major.lower()]

    def filter_by_year(self, year: int) -> list[Student]:
        return [s for s in self._students.values() if s.year == year]

    def count(self) -> int:
        return len(self._students)


class StudentManagementSystem:
    def __init__(self):
        self.repo = StudentRepository()

    def create_student(self) -> Optional[Student]:
        print("\n  — Enroll New Student —")
        first = input("  First name: ").strip()
        last = input("  Last name: ").strip()
        if not first or not last:
            print("  Name is required.")
            return None

        email = input("  Email: ").strip()
        if not email or "@" not in email:
            print("  Valid email is required.")
            return None

        if self.repo.find_by_email(email):
            print("  \033[91m✗ Email already registered.\033[0m")
            return None

        dob = input("  Date of birth (YYYY-MM-DD): ").strip()
        try:
            datetime.strptime(dob, "%Y-%m-%d")
        except ValueError:
            print("  Invalid date format.")
            return None

        major = input("  Major: ").strip() or "Undeclared"

        while True:
            try:
                year = int(input("  Year [1-4]: ").strip())
                if 1 <= year <= 4:
                    break
            except ValueError:
                pass
            print("  Enter a year between 1 and 4.")

        notes = input("  Notes (optional): ").strip()
        now = datetime.now().isoformat()

        student = Student(
            id=str(uuid.uuid4())[:8].upper(),
            first_name=first,
            last_name=last,
            email=email,
            date_of_birth=dob,
            major=major,
            year=year,
            enrolled=True,
            created_at=now,
            updated_at=now,
            notes=notes,
        )
        self.repo.add(student)
        print(f"\n  \033[92m✓ Student enrolled — ID: {student.id}\033[0m")
        return student

    def read_student(self, student_id: Optional[str] = None) -> Optional[Student]:
        if not student_id:
            student_id = input("\n  Student ID: ").strip().upper()
        student = self.repo.get(student_id)
        if not student:
            print("  \033[91m✗ Student not found.\033[0m")
            return None
        self._display_profile(student)
        return student

    def _display_profile(self, student: Student):
        w = 54
        gpa = student.gpa
        gpa_str = f"{gpa:.2f}" if gpa is not None else "N/A"
        gpa_color = (
            "\033[92m" if gpa and gpa >= 3.5 else
            "\033[96m" if gpa and gpa >= 3.0 else
            "\033[93m" if gpa and gpa >= 2.0 else
            "\033[91m"
        )
        year_labels = {1: "Freshman", 2: "Sophomore", 3: "Junior", 4: "Senior"}

        print(f"\n  ┌{'─' * w}┐")
        print(f"  │{'  STUDENT PROFILE':^{w}}│")
        print(f"  ├{'─' * w}┤")
        print(f"  │  {'ID':<20} {student.id:>{w - 23}}  │")
        print(f"  │  {'Name':<20} {student.full_name:>{w - 23}}  │")
        print(f"  │  {'Email':<20} {student.email:>{w - 23}}  │")
        print(f"  │  {'Date of Birth':<20} {student.date_of_birth + f' (age {student.age})':>{w - 23}}  │")
        print(f"  │  {'Major':<20} {student.major:>{w - 23}}  │")
        print(f"  │  {'Year':<20} {year_labels.get(student.year, str(student.year)):>{w - 23}}  │")
        print(f"  │  {'Status':<20} {'Enrolled' if student.enrolled else 'Withdrawn':>{w - 23}}  │")
        print(f"  │  {'GPA':<20} {gpa_color}{gpa_str:>{w - 23}}\033[0m  │")
        print(f"  │  {'Standing':<20} {student.standing:>{w - 23}}  │")
        print(f"  │  {'Total Credits':<20} {student.total_credits:>{w - 23}}  │")

        if student.notes:
            print(f"  ├{'─' * w}┤")
            print(f"  │  Notes: {student.notes[:w - 10]:<{w - 9}}│")

        records = student.course_records
        if records:
            print(f"  ├{'─' * w}┤")
            print(f"  │{'  COURSE RECORDS':^{w}}│")
            print(f"  ├{'─' * w}┤")
            print(f"  │  {'Code':<10} {'Course':<22} {'Cr':>3} {'Score':>6} {'Grade':>6}  │")
            print(f"  │  {'─' * 50}  │")
            for r in records:
                grade_color = "\033[92m" if r.grade_points >= 3.0 else "\033[93m" if r.grade_points >= 2.0 else "\033[91m"
                print(f"  │  {r.course_code:<10} {r.course_name[:20]:<22} {r.credits:>3} {r.score:>6.1f} {grade_color}{r.grade:>6}\033[0m  │")

        print(f"  └{'─' * w}┘")

    def update_student(self):
        student_id = input("\n  Student ID to update: ").strip().upper()
        student = self.repo.get(student_id)
        if not student:
            print("  \033[91m✗ Student not found.\033[0m")
            return

        print(f"\n  Updating: {student.full_name}")
        print("  (Press Enter to keep current value)\n")

        new_first = input(f"  First name [{student.first_name}]: ").strip() or student.first_name
        new_last = input(f"  Last name [{student.last_name}]: ").strip() or student.last_name
        new_email = input(f"  Email [{student.email}]: ").strip() or student.email
        new_major = input(f"  Major [{student.major}]: ").strip() or student.major
        new_notes = input(f"  Notes [{student.notes or '—'}]: ").strip() or student.notes

        year_input = input(f"  Year [{student.year}]: ").strip()
        try:
            new_year = int(year_input) if year_input else student.year
            if not (1 <= new_year <= 4):
                raise ValueError
        except ValueError:
            print("  Invalid year, keeping current.")
            new_year = student.year

        enrolled_input = input(f"  Enrolled [{student.enrolled}] (y/n): ").strip().lower()
        new_enrolled = student.enrolled
        if enrolled_input == "y":
            new_enrolled = True
        elif enrolled_input == "n":
            new_enrolled = False

        student.first_name = new_first
        student.last_name = new_last
        student.email = new_email
        student.major = new_major
        student.year = new_year
        student.enrolled = new_enrolled
        student.notes = new_notes
        student.updated_at = datetime.now().isoformat()

        self.repo.update(student)
        print(f"\n  \033[92m✓ Record updated.\033[0m")

    def delete_student(self):
        student_id = input("\n  Student ID to remove: ").strip().upper()
        student = self.repo.get(student_id)
        if not student:
            print("  \033[91m✗ Not found.\033[0m")
            return
        confirm = input(f"  Remove {student.full_name} permanently? [yes/N]: ").strip()
        if confirm.lower() == "yes":
            self.repo.delete(student_id)
            print("  \033[92m✓ Student record removed.\033[0m")
        else:
            print("  Cancelled.")

    def add_course(self):
        student_id = input("\n  Student ID: ").strip().upper()
        student = self.repo.get(student_id)
        if not student:
            print("  \033[91m✗ Not found.\033[0m")
            return

        print(f"\n  Adding course for {student.full_name}")
        code = input("  Course code (e.g. CS101): ").strip().upper()
        name = input("  Course name: ").strip()
        try:
            credits = int(input("  Credits (1-6): ").strip())
            score = float(input("  Score (0-100): ").strip())
        except ValueError:
            print("  Invalid input.")
            return

        if not (0 <= score <= 100):
            print("  Score must be between 0 and 100.")
            return

        semester = input("  Semester (e.g. Fall 2024): ").strip()

        record = CourseRecord(
            course_code=code,
            course_name=name,
            credits=credits,
            score=score,
            semester=semester,
        )
        student.courses.append(asdict(record))
        student.updated_at = datetime.now().isoformat()
        self.repo.update(student)

        grade = record.grade
        print(f"\n  \033[92m✓ Added {code} — Grade: {grade} (GPA: {student.gpa})\033[0m")

    def list_students(self):
        print("\n  — All Students —")
        students = self.repo.all()
        if not students:
            print("  No students enrolled.")
            return

        print(f"\n  {'ID':<10} {'Name':<26} {'Major':<20} {'Year':<6} {'GPA':<7} Standing")
        print("  " + "─" * 80)
        year_labels = {1: "Fr", 2: "So", 3: "Jr", 4: "Sr"}
        for s in students:
            gpa = s.gpa
            gpa_str = f"{gpa:.2f}" if gpa is not None else "N/A"
            color = (
                "\033[92m" if gpa and gpa >= 3.5 else
                "\033[96m" if gpa and gpa >= 3.0 else
                "\033[93m" if gpa and gpa >= 2.0 else
                "\033[91m" if gpa else "\033[0m"
            )
            status = "" if s.enrolled else " \033[91m[W]\033[0m"
            print(f"  {s.id:<10} {s.full_name[:24]:<26} {s.major[:18]:<20} {year_labels.get(s.year, str(s.year)):<6} {color}{gpa_str:<7}\033[0m {s.standing}{status}")

    def search_students(self):
        query = input("\n  Search (name / email / major / ID): ").strip()
        results = self.repo.search(query)
        if not results:
            print("  No matches.")
            return
        print(f"\n  {len(results)} result(s) found:\n")
        for s in results:
            gpa = s.gpa
            print(f"  [{s.id}] {s.full_name} — {s.major} — GPA: {f'{gpa:.2f}' if gpa else 'N/A'}")

    def class_analytics(self):
        students = self.repo.all()
        enrolled = [s for s in students if s.enrolled]
        gpas = [s.gpa for s in enrolled if s.gpa is not None]

        w = 50
        print(f"\n  ┌{'─' * w}┐")
        print(f"  │{'  CLASS ANALYTICS':^{w}}│")
        print(f"  ├{'─' * w}┤")
        print(f"  │  {'Total Students':<28} {len(students):>19}  │")
        print(f"  │  {'Currently Enrolled':<28} {len(enrolled):>19}  │")
        print(f"  │  {'Withdrawn':<28} {len(students) - len(enrolled):>19}  │")

        if gpas:
            print(f"  ├{'─' * w}┤")
            print(f"  │  {'Average GPA':<28} {mean(gpas):>18.2f}  │")
            print(f"  │  {'Median GPA':<28} {median(gpas):>18.2f}  │")
            if len(gpas) > 1:
                print(f"  │  {'Std Dev GPA':<28} {stdev(gpas):>18.2f}  │")
            print(f"  │  {'Highest GPA':<28} {max(gpas):>18.2f}  │")
            print(f"  │  {'Lowest GPA':<28} {min(gpas):>18.2f}  │")

            standing_count = {}
            for s in enrolled:
                st = s.standing
                standing_count[st] = standing_count.get(st, 0) + 1

            print(f"  ├{'─' * w}┤")
            print(f"  │{'  BY STANDING':^{w}}│")
            print(f"  ├{'─' * w}┤")
            for standing, count in sorted(standing_count.items(), key=lambda x: -x[1]):
                print(f"  │  {standing:<28} {count:>19}  │")

        major_count: dict[str, int] = {}
        for s in enrolled:
            major_count[s.major] = major_count.get(s.major, 0) + 1
        if major_count:
            print(f"  ├{'─' * w}┤")
            print(f"  │{'  BY MAJOR':^{w}}│")
            print(f"  ├{'─' * w}┤")
            for major, count in sorted(major_count.items(), key=lambda x: -x[1])[:8]:
                print(f"  │  {major[:26]:<28} {count:>19}  │")

        print(f"  └{'─' * w}┘")


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def banner(sms: StudentManagementSystem):
    count = sms.repo.count()
    print("\033[94m")
    print("  ╔══════════════════════════════════════════╗")
    print("  ║      STUDENT MANAGEMENT SYSTEM           ║")
    print(f"  ║      {count} student(s) enrolled{' ' * (18 - len(str(count)))}║")
    print("  ╚══════════════════════════════════════════╝")
    print("\033[0m")


def main():
    sms = StudentManagementSystem()

    options = {
        "1": ("Enroll Student", sms.create_student),
        "2": ("View Student Profile", sms.read_student),
        "3": ("Update Student", sms.update_student),
        "4": ("Remove Student", sms.delete_student),
        "5": ("Add Course Grade", sms.add_course),
        "6": ("List All Students", sms.list_students),
        "7": ("Search Students", sms.search_students),
        "8": ("Class Analytics", sms.class_analytics),
        "0": ("Exit", None),
    }

    while True:
        clear()
        banner(sms)
        print("  MAIN MENU\n")
        for key, (label, _) in options.items():
            print(f"    [{key}] {label}")
        print()

        choice = input("  Select option: ").strip()
        if choice == "0":
            print("\n  Goodbye.\n")
            break
        elif choice in options:
            _, action = options[choice]
            if action:
                action()
                input("\n  Press Enter to continue...")
        else:
            print("  Invalid option.")


if __name__ == "__main__":
    main()
