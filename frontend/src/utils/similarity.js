// Shared helper for turning a raw cosine-similarity score (0-1) from the
// CLO<->PLO and question<->CLO AI matching endpoints into a plain-language
// label. Non-technical faculty see "Strong"/"Moderate"/"Weak"; the raw score
// stays available for anyone who wants it (surfaced via InfoTooltip), it's
// just not the primary thing shown.
//
// Thresholds mirror the mapping-strength suggestion that already existed in
// MappingModal.jsx (strength 3/"Strong" at >=0.5, 2/"Moderate" at >=0.3), so
// the qualitative label and the auto-suggested mapping strength never
// disagree with each other.
export function similarityLabel(score) {
  if (score >= 0.5) return { label: 'Strong', tone: 'success' }
  if (score >= 0.3) return { label: 'Moderate', tone: 'warning' }
  return { label: 'Weak', tone: 'neutral' }
}

// Default mapping strength (1=weak, 2=moderate, 3=strong) suggested from a
// similarity score, so faculty aren't stuck picking a number blind -- they
// can still override it before confirming.
export function strengthFromSimilarity(score) {
  if (score >= 0.5) return 3
  if (score >= 0.3) return 2
  return 1
}
