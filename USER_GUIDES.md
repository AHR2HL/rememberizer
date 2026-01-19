# Rememberizer User Guides

Complete user guides for Admin, Teacher, and Student roles in Rememberizer.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Admin Guide](#admin-guide)
3. [Teacher Guide](#teacher-guide)
4. [Student Guide](#student-guide)
5. [Common Tasks](#common-tasks)
6. [Frequently Asked Questions](#frequently-asked-questions)

---

## Getting Started

### Logging In

1. **Navigate to the login page**: `http://yourserver.com/login`
2. **Enter your credentials**:
   - Email address (provided by your admin/teacher)
   - Password (set via magic link)
3. **Click [LOGIN]**

You'll be redirected to your role-specific dashboard:
- **Admin** → Admin Control Panel
- **Teacher** → Teacher Dashboard
- **Student** → My Domains

### First-Time Setup (Teachers and Students)

When your account is created, you'll receive a setup link:

1. **Check your email** for the subject "Set Your Password for Rememberizer"
2. **Click the magic link** (valid for 7 days)
3. **Set your password**:
   - Minimum 8 characters
   - Enter password twice for confirmation
4. **Click [SET PASSWORD]**
5. **You'll be redirected to the login page**
6. **Login with your email and new password**

**Note**: If you don't receive an email, ask your admin/teacher for the setup link.

### Logging Out

Click the **[LOGOUT]** link in the top navigation bar.

### Forgot Password

Currently, there's no self-service password reset. Contact your teacher (students) or admin (teachers) to:
- Receive a new setup link, or
- Have your password reset manually

---

## Admin Guide

### Role Overview

**Admin (Super User)** is the highest privilege level:
- Create and manage teacher accounts
- View system-wide overview
- Access all teacher functions
- Manage the entire organization

**Capabilities:**
- ✅ Create teacher accounts
- ✅ View all teachers
- ✅ Deactivate teacher accounts
- ✅ Access all teacher dashboards and functions
- ❌ Cannot directly access student quiz routes (by design)

### Admin Dashboard

**Access**: After login, you'll see the Admin Control Panel.

**Dashboard sections:**

#### 1. System Overview
Displays high-level statistics:
- **Teachers**: Total number of teacher accounts
- **Students**: Total number of student accounts across all teachers
- **Domains**: Total number of fact domains loaded from JSON files

#### 2. Teacher Management
Lists all teachers in the organization:
- Teacher name and email
- Creation date
- Deactivate button (disables teacher login)

#### 3. Create New Teacher
Button to add new teacher accounts.

### Creating a Teacher Account

**Step 1**: From Admin Dashboard, click **[CREATE NEW TEACHER]**

**Step 2**: Fill in the teacher information:
- **First Name**: Teacher's first name
- **Last Name**: Teacher's last name
- **Email**: Valid email address (must be unique)

**Step 3**: Click **[CREATE TEACHER]**

**What happens next:**
1. System creates teacher account with no password
2. System generates a secure setup token (valid 7 days)
3. System attempts to send email with setup link
4. **If email succeeds**: Teacher receives email and can set password
5. **If email fails**: Setup link is displayed on screen with instructions to share securely

**Best practices:**
- Use professional email addresses (e.g., `john.smith@school.edu`)
- Share setup links via secure channel if email fails (Slack DM, encrypted message)
- Setup links expire after 7 days - create new account if expired
- Verify email address before creating (typos prevent teacher access)

### Managing Teachers

#### View All Teachers

From Admin Dashboard, scroll to **TEACHER MANAGEMENT** section to see:
- Full name
- Email address
- Creation date

#### Deactivate Teacher Account

**When to deactivate:**
- Teacher no longer works at organization
- Temporary suspension needed
- Account security concerns

**How to deactivate:**
1. Find teacher in list
2. Click **[DEACTIVATE]** button
3. Confirm action
4. Teacher can no longer login (existing sessions terminated)

**Note**: Deactivating a teacher does NOT:
- Delete their students
- Delete student progress
- Delete domain assignments
- Delete the teacher account from database

**To reactivate** (requires database access):
```python
from app import app, db
from models import User

with app.app_context():
    teacher = User.query.filter_by(email='teacher@example.com').first()
    teacher.is_active = True
    db.session.commit()
```

### Viewing All Domains

Admins can access the **domains list** via the teacher routes:
1. Navigate to `/teacher/domains` (or via teacher dashboard)
2. View all loaded fact domains
3. See domain statistics

### Best Practices for Admins

1. **Create teachers first**: Teachers create students, so onboard teachers before students
2. **Verify emails**: Double-check email addresses before creating accounts
3. **Secure setup links**: Share setup links via secure channels (not public forums)
4. **Regular backups**: Ensure database backups are configured (see INSTALLATION.md)
5. **Monitor activity**: Periodically review teacher and student counts
6. **Deactivate promptly**: Deactivate accounts immediately when staff leaves
7. **Strong admin password**: Use a unique, strong password for admin account
8. **Limit admin accounts**: Only create admin accounts for IT staff/system administrators

### Admin Troubleshooting

#### "Email already exists" When Creating Teacher

**Cause**: Email address is already in use.

**Solution**:
- Check if teacher account already exists
- Use a different email address
- Or delete the existing account from database if it's a duplicate

#### Setup Link Expired

**Cause**: Teacher didn't set password within 7 days.

**Solution**:
- Create a new teacher account with same information
- Teacher will receive new setup link
- Old account can be deleted from database if needed

#### Teacher Can't Login After Setup

**Diagnosis checklist**:
- [ ] Did teacher complete password setup?
- [ ] Is teacher entering correct email and password?
- [ ] Is teacher account active (`is_active=TRUE`)?
- [ ] Are there any server errors in logs?

---

## Teacher Guide

### Role Overview

**Teacher** is the primary user management role:
- Create and manage student accounts
- Assign domains to students
- View detailed student progress
- Track engagement metrics
- Reset student progress

**Capabilities:**
- ✅ Create student accounts
- ✅ Assign/unassign domains to/from students
- ✅ View all students in their organization
- ✅ View detailed student progress
- ✅ Reset student progress for specific domains
- ✅ Track engagement metrics (questions, time, sessions)
- ❌ Cannot access students from other organizations
- ❌ Cannot create other teachers (only admin can)
- ❌ Cannot access student quiz routes directly

### Teacher Dashboard

**Access**: After login, you'll see the Teacher Dashboard.

**Dashboard sections:**

#### 1. My Students List
Displays all students you've created:
- Student name and email
- Number of assigned domains (e.g., "Domains: 2/2")
- Last active timestamp
- Total questions answered
- Questions answered today
- Quick progress preview (visual progress bars)
- Action buttons: [VIEW DETAILS] and [MANAGE DOMAINS]

#### 2. Create New Student
Button to add new student accounts.

### Creating a Student Account

**Step 1**: From Teacher Dashboard, click **[CREATE NEW STUDENT]**

**Step 2**: Fill in the student information:
- **First Name**: Student's first name
- **Last Name**: Student's last name
- **Email**: Valid email address (must be unique)

**Step 3**: Click **[CREATE STUDENT]**

**What happens next:**
1. System creates student account with no password
2. System generates a secure setup token (valid 7 days)
3. System attempts to send email with setup link
4. **If email succeeds**: Student receives email and can set password
5. **If email fails**: Setup link is displayed on screen with instructions to share securely

**Best practices:**
- Use student's school email if available
- Or use parent email for younger students
- Share setup links securely (don't post publicly)
- Verify email spelling before creating
- Consider creating accounts in batches at start of term

### Assigning Domains to Students

**Why assign domains?**
Students can only practice domains that are explicitly assigned to them. This allows you to:
- Control what content each student accesses
- Differentiate instruction (different students, different domains)
- Gradually release content
- Prevent students from accessing inappropriate/advanced content

**How to assign domains:**

**Method 1: From Student Detail Page**
1. Click **[VIEW DETAILS]** for a student
2. Scroll to **DOMAIN PROGRESS** section
3. Find unassigned domain
4. Click **[ASSIGN DOMAIN]**
5. Domain is now accessible to student

**Method 2: From Dashboard**
1. Click **[MANAGE DOMAINS]** next to student name
2. View all domains (assigned and unassigned)
3. Click **[ASSIGN]** for domains you want student to access

**What happens when you assign:**
- Student immediately sees domain in their "My Domains" page
- Student can click "Start Practice" to begin quizzing
- Domain progress tracking begins

### Unassigning Domains from Students

**When to unassign:**
- Student completed domain and no longer needs access
- Student moved to different learning path
- Domain was assigned by mistake

**How to unassign:**
1. Go to student detail page
2. Find assigned domain in **DOMAIN PROGRESS** section
3. Click **[UNASSIGN]**
4. Confirm action
5. Domain is removed from student's access

**Note**: Unassigning does NOT:
- Delete student progress (progress is preserved)
- Delete attempts or fact states (data remains in database)
- If you re-assign the domain later, progress will still be there

### Viewing Student Progress

**Access student detail page:**
1. From Teacher Dashboard
2. Click **[VIEW DETAILS]** next to student name

**Student Detail Page sections:**

#### 1. Profile Information
- Student name
- Email address
- Last active timestamp
- Total time spent (estimated)
- Total questions answered

#### 2. Engagement Metrics
- **Total Questions**: Lifetime question count
- **Questions Today**: Questions answered today (resets at midnight UTC)
- **Total Time Spent**: Estimated time from first to last attempt (formatted as "2h 15m")
- **Practice Sessions**: Number of unique quiz sessions

**Note**: Time is estimated from first attempt to last attempt timestamp, not actual active engagement time.

#### 3. Domain Progress
For each assigned domain:
- Domain name
- Visual progress bar (using terminal characters):
  - `·` (dot) = Unlearned fact
  - `+` (plus) = Learned fact (not yet mastered)
  - `*` (asterisk) = Mastered fact
  - `-` (dash) = Fact demoted to unlearned (needs review)
- **Learned**: Count of learned facts / total facts
- **Mastered**: Count of mastered facts / total facts
- **Time**: Time spent on this domain
- **Attempts**: Total quiz attempts for this domain
- Action buttons: [VIEW DETAILS], [RESET], [UNASSIGN]

**Example progress bar:**
```
Progress: ········++++****
```
Means: 8 unlearned, 4 learned, 4 mastered (16 facts total)

#### 4. Domain Detail View
Click **[VIEW DETAILS]** on a domain to see:
- Detailed fact-by-fact progress
- Mastery status for each fact
- Recent attempts
- Time spent per fact

### Resetting Student Progress

**When to reset:**
- Student wants to start fresh
- Student needs to review material from beginning
- Practice test/assessment period ended
- Domain content was updated

**How to reset:**
1. Go to student detail page
2. Find domain in **DOMAIN PROGRESS** section
3. Click **[RESET]** button
4. Confirm action

**What reset does:**
- Clears all FactState records for that student in that domain
- Deletes all Attempt records for that student in that domain
- Student must re-learn and re-quiz all facts
- Progress bar returns to all dots: `················`

**What reset does NOT do:**
- Affect other students' progress
- Affect other domains
- Unassign the domain (student still has access)

**Warning**: Reset is **irreversible**. Student will lose all progress permanently.

### Understanding Progress Indicators

#### Progress Bar Symbols
- **`·`** (dot): Unlearned - Fact has never been shown or was demoted after 2 wrong answers
- **`+`** (plus): Learned - Fact was shown and student clicked "Continue", but not yet mastered
- **`-`** (dash): Demoted - Fact was learned but student got 2 consecutive wrong answers
- **`*`** (asterisk): Mastered - Student achieved 6+ correct in last 7 attempts with most recent correct

#### Engagement Metrics Explained

**Questions Answered Today:**
- Counts all quiz attempts since midnight UTC
- Resets daily at 00:00 UTC
- Useful for tracking daily engagement

**Total Time Spent:**
- Calculated as: (last attempt timestamp) - (first attempt timestamp)
- **NOT** actual active time (includes breaks, pauses, etc.)
- Formatted as "1h 30m" or "45m"
- Useful for rough engagement estimate

**Practice Sessions:**
- Each time student clicks "Start Practice", new session ID generated
- Counts unique session IDs in attempts
- Useful for tracking frequency of practice (not duration)

**Last Active:**
- Timestamp of last request (any page view, any action)
- Updated automatically on every request
- Useful for identifying inactive students

### Managing Multiple Students

**Tips for large classes:**

1. **Use naming conventions**: Create students with consistent naming (e.g., "Smith, John" format)
2. **Assign domains in batches**: Assign same domain to all students at once (requires multiple clicks, but systematic)
3. **Monitor engagement**: Sort by "Last Active" to identify students who haven't logged in
4. **Track daily questions**: Identify students answering 0 questions today
5. **Progressive release**: Assign domains gradually as students master previous content

**Workflow for new term:**
1. Create all student accounts (share setup links via class email/LMS)
2. Wait for students to set passwords and log in
3. Assign first domain to all students
4. Monitor progress over first week
5. Assign additional domains as students demonstrate mastery

### Deactivating Students

**Note**: Currently, teachers cannot deactivate students via UI. This requires database access or admin intervention.

**To request student deactivation:**
- Contact your system administrator
- Provide student email address
- Admin can deactivate via database or future admin UI

**When to deactivate:**
- Student dropped class
- Student transferred schools
- Account security concerns

### Best Practices for Teachers

1. **Create students early**: Give students time to set passwords before first assignment
2. **Verify emails**: Double-check spelling (typos prevent student access)
3. **Share setup links securely**: Use LMS, school email, or direct message (not public posts)
4. **Assign domains purposefully**: Don't assign all domains at once (progressive release is better)
5. **Monitor regularly**: Check dashboard weekly to identify struggling students
6. **Reset sparingly**: Reset is irreversible - only use when truly needed
7. **Communicate expectations**: Tell students how many questions per day you expect
8. **Provide feedback**: Use engagement metrics to provide specific feedback ("I noticed you haven't practiced this week")

### Teacher Troubleshooting

#### Student Says They Can't See a Domain

**Diagnosis:**
1. Go to student detail page
2. Check if domain is assigned
3. If not assigned: Click [ASSIGN DOMAIN]
4. Ask student to refresh their page

#### Student Forgot Password

**Solution:**
1. Create a new student account with same name, different email (or add ".2" to email)
2. Share new setup link with student
3. Assign same domains to new account
4. Old account can be deactivated

**Note**: Progress cannot be transferred between accounts. Student will start fresh.

#### Progress Bar Shows All Dashes `----------`

**Meaning**: Student got 2 consecutive wrong answers on many facts, causing demotion.

**This is normal behavior**: The system automatically demotes facts when student struggles.

**What to do**:
- Student needs to review facts again (system will show facts before re-quizzing)
- Consider reviewing the material with student before they practice again
- Or reset domain progress for a fresh start

#### Student Sees "You don't have access to this domain"

**Cause**: Domain is not assigned to that student.

**Solution**: Assign the domain from student detail page.

#### Engagement Metrics Show 0 Time Spent

**Cause**: Student has fewer than 2 attempts (time requires at least 2 attempts to calculate delta).

**Solution**: Normal for new students. Metrics will populate after student answers a few questions.

---

## Student Guide

### Role Overview

**Student** is the learner role:
- View assigned domains
- Practice quiz questions
- Track personal progress
- View engagement metrics
- Reset own progress

**Capabilities:**
- ✅ View only assigned domains
- ✅ Practice quiz questions on assigned domains
- ✅ View personal progress and metrics
- ✅ Reset own progress (start over)
- ❌ Cannot access unassigned domains
- ❌ Cannot see other students' progress
- ❌ Cannot assign domains to themselves
- ❌ Cannot create accounts

### Student Dashboard ("My Domains")

**Access**: After login, you'll see "MY DOMAINS" page.

**Dashboard shows:**
- List of your assigned domains
- Progress bar for each domain
- Statistics: Learned / Total facts, Mastered / Total facts
- **[START PRACTICE]** button for each domain
- Today's stats: Questions answered today, Time spent today

**Example:**
```
╔═══════════════════════════════════╗
║    REMEMBERIZER v3.0             ║
╚═══════════════════════════════════╝

Logged in as: Alice Johnson [LOGOUT]

> YOUR ASSIGNED DOMAINS

[1] Greek Muses
    Progress: ········++++****
    Learned: 8/16 | Mastered: 4/16
    [START PRACTICE]

[2] Chinese Dynasties
    Progress: ··············
    Learned: 0/14 | Mastered: 0/14
    [START PRACTICE]

────────────────────────────────────
Questions Today: 12 | Time Today: 45m
```

### Starting a Practice Session

**Step 1**: From "My Domains" page, click **[START PRACTICE]** for a domain

**Step 2**: System checks your progress:
- If you have unlearned facts: System shows you the next unlearned fact
- If all facts are learned: System starts quizzing learned facts

### Learning New Facts

**When you see a fact card:**

**Example:**
```
╔═══════════════════════════════════╗
║    GREEK MUSE                    ║
╚═══════════════════════════════════╝

Name: Calliope
Domain Of Expertise: Epic Poetry
Symbol: Writing Tablet

[CONTINUE]
```

**What to do:**
1. **Read the fact carefully**: Memorize the information
2. **Click [CONTINUE]** when ready to be quizzed
3. System marks fact as "learned" and generates quiz question

**Important**: You must click [CONTINUE] to mark the fact as learned. Simply viewing the fact is not enough.

### Answering Quiz Questions

**After marking a fact as learned, you'll see a quiz question:**

**Example:**
```
╔═══════════════════════════════════╗
║    QUIZ: GREEK MUSE              ║
╚═══════════════════════════════════╝

What is the Domain Of Expertise of Calliope?

[A] Epic Poetry
[B] Lyric Poetry
[C] Dance
[D] Tragedy

Question 5/16
```

**What to do:**
1. **Read the question carefully**
2. **Select your answer** (A, B, C, or D)
3. **Click [SUBMIT]** or press the corresponding key
4. System shows whether you were correct or incorrect

### Understanding Answer Results

**Correct Answer:**
```
✓ CORRECT!

The correct answer is: Epic Poetry

You got this one right!

[NEXT QUESTION]
```

**Incorrect Answer:**
```
✗ INCORRECT

You answered: Dance
The correct answer is: Epic Poetry

Let's review this fact and try again.

[CONTINUE]
```

**What happens after incorrect answer:**
- System increments your "consecutive wrong" counter
- If this is your 2nd consecutive wrong answer: Fact is **demoted to unlearned**
  - You'll see the fact card again
  - Must click [CONTINUE] to re-learn
  - Then you'll be quizzed again
- If this is your 1st wrong answer: You'll see the fact card, then re-quiz

### Mastering Facts

**How to master a fact:**
- Answer questions about that fact correctly
- Achieve 6+ correct answers in the last 7 attempts
- **AND** your most recent attempt must be correct
- Requires minimum 7 attempts

**Example progress toward mastery:**
- Attempt 1: ✓ Correct
- Attempt 2: ✓ Correct
- Attempt 3: ✗ Wrong
- Attempt 4: ✓ Correct
- Attempt 5: ✓ Correct
- Attempt 6: ✓ Correct
- Attempt 7: ✓ Correct
- **Result**: 6 out of 7 correct, most recent correct → **MASTERED** ⭐

**Visual indicators:**
- Progress bar shows `*` for mastered facts
- Mastered count increases: "Mastered: 5/16"

### Spaced Repetition (Reinforcement Questions)

**Every 3rd question**, the system will quiz you on a **mastered fact** for reinforcement:

**Why?**
- Prevents forgetting (spaced repetition)
- Maintains long-term retention
- Ensures you don't lose mastery

**What to do:**
- Treat it like any other question
- Answer correctly to maintain mastery
- If you get it wrong: Fact may be demoted (depending on consecutive wrong counter)

### Progress Tracking

**View your progress:**
- From "My Domains" page: See high-level progress for all domains
- Click [VIEW PROGRESS] (if available) for detailed personal stats

**Progress metrics:**
- **Learned**: Facts you've seen and clicked "Continue" on
- **Mastered**: Facts with 6/7 correct and most recent correct
- **Questions Today**: Count of questions answered since midnight (UTC)
- **Time Today**: Estimated time from first to last question today
- **Total Questions**: All-time question count
- **Practice Sessions**: Number of times you've clicked "Start Practice"

### Resetting Your Progress

**When to reset:**
- You want to start over from the beginning
- You feel like you've forgotten the material
- You want to re-learn everything systematically

**How to reset:**
1. From "My Domains" page, find the domain
2. Click **[RESET PROGRESS]** (or from quiz page, click [RESET])
3. Confirm action

**What reset does:**
- Erases all your progress for that domain
- All facts return to "unlearned" status
- All previous attempts are deleted
- Progress bar returns to: `················`
- You'll start from scratch (fact #1 shown again)

**Warning**: Reset is **irreversible**. You cannot undo it.

### Tips for Effective Learning

#### 1. Practice Regularly
- **Daily practice** is more effective than cramming
- Aim for at least 10-20 questions per day
- Short sessions (15-20 minutes) work well

#### 2. Focus on Mastery
- Don't rush through facts
- Read each fact carefully before clicking [CONTINUE]
- If you get 2 wrong in a row, take a break and review

#### 3. Use the Progress Bar
- Check your progress bar to see where you stand
- `·` dots = Need to learn
- `+` pluses = Know, but not mastered yet
- `*` asterisks = Mastered (great job!)
- `-` dashes = Need to review (got 2 wrong)

#### 4. Learn from Mistakes
- When you get a question wrong, read the correct answer carefully
- Click [CONTINUE] on the fact review and really study it
- Try to understand WHY the correct answer is correct

#### 5. Track Your Engagement
- Notice "Questions Today" count on dashboard
- Set personal goals (e.g., "answer 20 questions today")
- Celebrate progress (e.g., "I mastered 5 new facts this week!")

### Student Troubleshooting

#### I Can't See Any Domains

**Cause**: No domains have been assigned to you yet.

**Solution**: Ask your teacher to assign domains to your account.

#### I See "You don't have access to this domain"

**Cause**: You tried to access a domain that isn't assigned to you.

**Solution**:
- Go back to "My Domains" page
- Only practice domains shown in your list
- Ask teacher if you need access to a different domain

#### I Forgot My Password

**Solution**:
- Contact your teacher
- Teacher will create a new account for you
- You'll receive a new setup link to set a new password

**Note**: Your progress cannot be transferred. You'll start fresh with the new account.

#### Progress Bar Shows All Dashes `----------`

**Meaning**: You got 2 consecutive wrong answers on many facts.

**This is normal**: The system demotes facts when you struggle, so you can re-learn them.

**What to do**:
- When you see a fact card, read it VERY carefully
- Take your time
- Maybe take a break and come back later
- Consider reviewing notes or materials before practicing

#### Same Question Over and Over

**Cause**: You haven't gotten 2 consecutive correct answers yet.

**How the system works**:
- You must answer correctly twice in a row before moving to next fact
- This ensures you really know the material
- If you get one right, then one wrong: Counter resets

**What to do**:
- Focus on that fact
- Read it carefully
- Answer correctly twice in a row
- Then system will move to next fact

#### Questions Today Count Doesn't Match

**Cause**: "Questions Today" resets at midnight UTC (may not be your local timezone).

**This is normal**: The count resets at a fixed time (00:00 UTC).

**Example**: If you practice at 11 PM and the count resets at midnight, your evening session might span two "days" in the system.

---

## Common Tasks

### Changing Your Password

**Current limitation**: No self-service password change.

**Workaround**:
- Contact your teacher/admin
- They can create a new account with new setup link
- Or manually reset your password in database

**Future enhancement**: Self-service password change planned for future version.

### Viewing Fact Domains

**Admin/Teacher**:
- Navigate to `/teacher/domains` to see all loaded domains
- Shows domain name, number of facts, fields

**Student**:
- Can only see assigned domains on "My Domains" page
- Cannot view unassigned domains

### Adding New Fact Domains (Admin/Teacher)

**Note**: Adding domains requires file system access.

**How to add**:
1. Create JSON file in `facts/` directory
2. Use this format:
```json
{
  "domain_name": "US Presidents",
  "fields": ["name", "party", "years_in_office"],
  "facts": [
    {
      "name": "George Washington",
      "party": "None",
      "years_in_office": "1789-1797"
    }
  ]
}
```
3. Restart application
4. Domain loads automatically

See README.md "Adding New Fact Domains" for details.

### Exporting Student Data

**Teacher workflow**:
1. View student detail page
2. Record statistics manually (screenshot or copy to spreadsheet)
3. Or contact admin for database export

**Future enhancement**: CSV export planned for future version.

---

## Frequently Asked Questions

### General Questions

**Q: How do I recover a deleted account?**
A: Accounts are not deleted, only deactivated. Contact your admin to reactivate.

**Q: Can I have multiple roles?**
A: No. Each account has exactly one role (admin, teacher, or student).

**Q: Can I transfer progress between accounts?**
A: No. Progress is tied to specific user accounts and cannot be transferred.

**Q: How long does my session last?**
A: Default is 24 hours of inactivity. You'll need to login again after that.

**Q: Is my data secure?**
A: Yes. Passwords are hashed with industry-standard scrypt. Sessions use secure cookies. See SECURITY.md for details.

### For Students

**Q: Why can't I access a domain?**
A: Only assigned domains are accessible. Ask your teacher to assign it.

**Q: What does "mastered" mean?**
A: You've answered 6+ out of the last 7 attempts correctly, and your most recent attempt was correct.

**Q: Why do I see the same question multiple times?**
A: You need 2 consecutive correct answers before moving to the next fact. Also, mastered facts appear every 3rd question for reinforcement.

**Q: Can I skip facts I already know?**
A: No. The system requires you to demonstrate mastery by answering correctly.

**Q: What happens if I reset my progress?**
A: All your progress for that domain is permanently deleted. You start from scratch.

### For Teachers

**Q: Can I create other teachers?**
A: No. Only admins can create teacher accounts.

**Q: Can I see other teachers' students?**
A: No. You only see students you've created in your organization.

**Q: What if a student forgets their password?**
A: Create a new account for them. Progress cannot be transferred.

**Q: Can I un-reset a student's progress?**
A: No. Reset is irreversible.

**Q: How is "time spent" calculated?**
A: From first attempt timestamp to last attempt timestamp. It's an estimate, not actual active time.

**Q: Can I assign multiple domains at once?**
A: Currently requires one click per domain. Bulk assignment planned for future version.

### For Admins

**Q: Can I create multiple admin accounts?**
A: Yes, but requires database access. See INSTALLATION.md for instructions.

**Q: How do I back up the database?**
A: See INSTALLATION.md "Backup and Recovery" section.

**Q: Can I delete users?**
A: Yes, via database access. But deactivation is recommended (preserves data).

**Q: How do I migrate to PostgreSQL?**
A: See INSTALLATION.md "Database Setup → PostgreSQL" section.

**Q: Can I support multiple organizations?**
A: Schema supports it, but UI currently assumes single organization. Multi-org support is a future enhancement.

---

## Getting Help

- **Technical issues**: See INSTALLATION.md "Troubleshooting" section
- **Security questions**: See SECURITY.md
- **Feature requests**: File an issue on GitHub
- **Bug reports**: File an issue on GitHub with detailed description
