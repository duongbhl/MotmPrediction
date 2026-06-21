const GK_SET  = new Set(['GK'])
const DEF_SET = new Set(['DC','DL','DR','DLC','DRC','WBL','WBR'])
const MID_SET = new Set(['DMC','MC','ML','MR','MLC','MRC','AMC','AML','AMR'])

export function posGroup(pos = '') {
  const p = pos.toUpperCase().trim()
  if (GK_SET.has(p))  return 'GK'
  if (DEF_SET.has(p)) return 'DEF'
  if (MID_SET.has(p)) return 'MID'
  return 'FWD'
}

export function initials(name = '') {
  return name.split(' ').map(w => w[0] || '').join('').slice(0, 2).toUpperCase() || '?'
}
