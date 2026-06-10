import { useState } from 'react'

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

const POS_STYLES = {
  GK:  'bg-gold/10 text-gold',
  DEF: 'bg-blue/10 text-blue',
  MID: 'bg-green/10 text-green',
  FWD: 'bg-red/10 text-red',
}

const statFields = [
  ['⭐ Rating',   'rating',         '0.1', true],
  ['⚽ Goals',    'goals',          '1',   false],
  ['🎯 Assists',  'assists',        '1',   false],
  ['🔫 Shots',    'shots_total',    '1',   false],
  ['🎯 On Tgt',   'shots_on_target','1',   false],
  ['🔑 Key Pass', 'key_passes',     '1',   false],
  ['⚔️ Tackles',  'tackles',        '1',   false],
  ['✂️ Intercp',  'interceptions',  '1',   false],
  ['⏱ Minutes',  'minutes_played', '1',   false],
]

const inputBase = 'w-full bg-white/[0.04] border border-white/[0.06] rounded-[7px] text-text text-sm font-bold text-center py-[7px] focus:outline-none focus:border-green focus:ring-2 focus:ring-green/10 transition-all'

function PlayerCard({ player, index, side, onUpdate, onRemove }) {
  const [open, setOpen] = useState(false)
  const pg    = posGroup(player.position)
  const avBg  = side === 'home'
    ? 'bg-gradient-to-br from-green to-[#00C45A] text-[#060B14]'
    : 'bg-gradient-to-br from-blue to-[#6366F1] text-white'

  const set = (key, val) =>
    onUpdate(index, { ...player, [key]: isNaN(parseFloat(val)) ? val : parseFloat(val) })

  return (
    <div className={`border rounded-[10px] mb-[7px] overflow-hidden transition-all duration-200 hover:-translate-y-[1px] ${open ? 'border-green' : 'border-white/[0.06] hover:border-green/20'}`}>

      {/* Header row */}
      <div
        className="flex items-center gap-2.5 px-[13px] py-[11px] cursor-pointer bg-white/[0.015] hover:bg-white/[0.03] transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <div className={`w-[34px] h-[34px] rounded-full flex items-center justify-center text-[13px] font-extrabold shrink-0 tracking-tighter ${avBg}`}>
          {initials(player.name)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-semibold truncate">{player.name}</div>
          <div className="text-[10px] text-muted mt-[1px]">{player.position} · {player.minutes_played}′</div>
        </div>
        <span className={`text-[9px] font-extrabold px-[7px] py-[3px] rounded-[5px] tracking-[0.6px] shrink-0 ${POS_STYLES[pg]}`}>{pg}</span>
        <span className={`text-[10px] text-muted ml-1 shrink-0 transition-transform duration-200 ${open ? 'rotate-180 !text-green' : ''}`}>▼</span>
      </div>

      {/* Expanded stats */}
      {open && (
        <div className="px-[13px] pb-[13px] pt-[14px] border-t border-white/[0.06] bg-green/[0.018]">
          <div className="grid grid-cols-3 gap-2.5">
            {statFields.map(([lbl, key, step, isRating]) => (
              <div key={key} className="flex flex-col gap-1">
                <label className="text-[9px] font-bold uppercase tracking-[1.4px] text-muted">{lbl}</label>
                <input
                  type="number" step={step}
                  value={player[key]}
                  className={`${inputBase} ${isRating ? 'text-gold' : ''}`}
                  onChange={e => set(key, e.target.value)}
                />
              </div>
            ))}
          </div>
          <div className="flex justify-end mt-[9px]">
            <button
              className="px-3 py-[5px] bg-red/10 border border-red/[0.18] rounded-[7px] text-red text-[11px] font-semibold hover:bg-red/20 transition-colors"
              onClick={() => onRemove(index)}
            >
              Remove
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function LineupPanel({ side, team, players, setPlayers, onAddManual }) {
  const isHome = side === 'home'

  const handleUpdate = (i, updated) =>
    setPlayers(prev => prev.map((p, idx) => idx === i ? updated : p))
  const handleRemove = (i) =>
    setPlayers(prev => prev.filter((_, idx) => idx !== i))

  return (
    <div className="bg-card border border-white/[0.06] hover:border-white/[0.12] rounded-[14px] transition-colors">
      {/* Card header */}
      <div className="flex items-center gap-2.5 px-[22px] pt-[18px] mb-[18px]">
        <div className={`w-[30px] h-[30px] rounded-[8px] flex items-center justify-center text-[15px] ${isHome ? 'bg-green/10' : 'bg-blue/10'}`}>
          {isHome ? '🏠' : '✈️'}
        </div>
        <span className="text-[11px] font-bold tracking-[1.8px] uppercase text-dim">
          {isHome ? 'Home XI' : 'Away XI'}
        </span>
      </div>

      {/* Body */}
      <div className="px-[18px] pb-[18px]">
        <div className="flex items-center justify-between mb-[14px]">
          <span className="text-[15px] font-bold">{team || '—'}</span>
          <span className={`text-[10px] font-bold px-[9px] py-[3px] rounded-full ${isHome ? 'bg-green/10 text-green' : 'bg-blue/10 text-blue'}`}>
            {players.length} player{players.length !== 1 ? 's' : ''}
          </span>
        </div>

        {players.length === 0 ? (
          <div className="text-center py-[22px] text-xs text-muted">
            {team ? 'No players yet' : `Select ${isHome ? 'home' : 'away'} team to load players`}
          </div>
        ) : (
          players.map((p, i) => (
            <PlayerCard
              key={`${side}-${i}`}
              player={p} index={i} side={side}
              onUpdate={handleUpdate}
              onRemove={handleRemove}
            />
          ))
        )}

        <button
          className="w-full py-[10px] mt-[5px] bg-transparent border border-dashed border-white/[0.06] rounded-[10px] text-muted text-xs cursor-pointer hover:border-green hover:text-green hover:bg-green/10 transition-all duration-200"
          onClick={onAddManual}
        >
          ＋ Add Player Manually
        </button>
      </div>
    </div>
  )
}


