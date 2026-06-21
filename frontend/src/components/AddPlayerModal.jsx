import { useState } from 'react'

const POSITIONS = [
  { value: 'GK',  label: 'GK — Goalkeeper' },
  { value: 'DC',  label: 'DC — Centre Back' },
  { value: 'DL',  label: 'DL — Left Back' },
  { value: 'DR',  label: 'DR — Right Back' },
  { value: 'DMC', label: 'DMC — Defensive Mid' },
  { value: 'MC',  label: 'MC — Central Mid' },
  { value: 'ML',  label: 'ML — Left Mid' },
  { value: 'MR',  label: 'MR — Right Mid' },
  { value: 'AMC', label: 'AMC — Attacking Mid' },
  { value: 'AML', label: 'AML — Left Wing' },
  { value: 'AMR', label: 'AMR — Right Wing' },
  { value: 'ST',  label: 'ST — Striker' },
]

const FIELDS = [
  ['Player Name',      'name',             'text',   '',    ''],
  ['Position',         'position',         'select', '',    'MC'],
  ['Age',              'age',              'number', '1',   ''],
]

const fieldCls = 'w-full bg-white/[0.04] border border-white/[0.06] rounded-[8px] text-text text-sm px-3 py-2.5 focus:outline-none focus:border-green focus:ring-2 focus:ring-green/10 transition-all'

export default function AddPlayerModal({ side, team, onClose, onSave }) {
  const defaults = Object.fromEntries(FIELDS.map(([, key, , , def]) => [key, def]))
  const [form, setForm] = useState(defaults)

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const save = () => {
    const p = {
      ...form,
      team,
      is_home:         side === 'home' ? 1 : 0,
      is_first_eleven: 1,
      age:              form.age ? parseFloat(form.age) : null,
    }
    onSave(p)
  }

  return (
    <div
      className="fixed inset-0 z-[500] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-card border border-white/[0.12] rounded-[16px] w-full max-w-[520px] max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-white/[0.06]">
          <span className="text-base font-bold">Add Player — {team || 'Team'}</span>
          <button
            className="w-[28px] h-[28px] rounded-full bg-white/[0.06] text-muted hover:bg-white/10 hover:text-text flex items-center justify-center text-sm transition-colors"
            onClick={onClose}
          >✕</button>
        </div>

        {/* Form grid */}
        <div className="p-6 grid grid-cols-2 gap-3">
          {FIELDS.map(([label, key, type, step]) => (
            <div key={key} className={`flex flex-col gap-1 ${key === 'name' ? 'col-span-2' : ''}`}>
              <label className="text-[10px] font-bold uppercase tracking-[1.6px] text-muted">{label}</label>
              {type === 'select' ? (
                <select value={form[key]} onChange={e => set(key, e.target.value)} className={fieldCls}>
                  {POSITIONS.map(p => (
                    <option key={p.value} value={p.value} className="bg-[#0D1420]">{p.label}</option>
                  ))}
                </select>
              ) : (
                <input
                  type={type}
                  step={step || undefined}
                  value={form[key]}
                  placeholder={key === 'name' ? 'e.g. Mohamed Salah' : undefined}
                  onChange={e => set(key, e.target.value)}
                  className={fieldCls}
                />
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="flex gap-3 px-6 pb-5">
          <button
            className="flex-1 py-[11px] rounded-[10px] border border-white/[0.1] bg-white/[0.04] text-dim text-sm font-semibold hover:bg-white/[0.07] transition-colors"
            onClick={onClose}
          >Cancel</button>
          <button
            className="flex-[2] py-[11px] rounded-[10px] bg-gradient-to-r from-green to-[#00B8FF] text-[#060B14] text-sm font-extrabold hover:shadow-[0_0_20px_rgba(0,232,122,0.35)] transition-all"
            onClick={save}
          >Add to Lineup</button>
        </div>
      </div>
    </div>
  )
}
