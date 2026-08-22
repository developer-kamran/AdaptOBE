// Mirrors backend/app/core/institution.py's expected_seat_no_year /
// seat_no_batch_year / is_backlog_batch_year exactly -- a "backlog" student
// is a computed fact (their seat number's encoded enrollment year is
// earlier than what this course's semester currently expects), not
// something the API flags explicitly. Keep this in lockstep with that
// module if its logic ever changes.

// Two semesters per academic year, so being in semester N means having
// enrolled N // 2 years before the current calendar year.
export function expectedSeatNoYear(semester) {
  return new Date().getFullYear() - Math.floor(semester / 2)
}

// Extracts the 4-digit enrollment year encoded in a seat number like
// "B221101...0001" (-> 2022). null if it doesn't start with the expected
// `B<2-digit year>` shape.
export function seatNoBatchYear(seatNo) {
  if (!seatNo || seatNo.length < 3 || seatNo[0] !== 'B' || !/^\d{2}$/.test(seatNo.slice(1, 3))) {
    return null
  }
  return 2000 + Number(seatNo.slice(1, 3))
}

// True if `seatNo`'s encoded enrollment year is strictly earlier than a
// current-batch student's for this semester -- i.e. this student is
// repeating the course from an earlier cohort. False for a seat number that
// doesn't parse, since backlog status can't be confirmed either way.
export function isBacklogStudent(seatNo, semester) {
  const batchYear = seatNoBatchYear(seatNo)
  if (batchYear === null) return false
  return batchYear < expectedSeatNoYear(semester)
}
