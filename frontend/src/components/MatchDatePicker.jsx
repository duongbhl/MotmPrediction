import { useEffect, useRef, useState } from 'react'
import { format, parseISO } from 'date-fns'
import { DayPicker } from 'react-day-picker'
import 'react-day-picker/style.css'

const toIsoDate = date => format(date, 'yyyy-MM-dd')

export default function MatchDatePicker({ value, onChange }) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)
  const selected = value ? parseISO(value) : undefined

  useEffect(() => {
    const closeOnOutsideClick = event => {
      if (!rootRef.current?.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', closeOnOutsideClick)
    return () => document.removeEventListener('mousedown', closeOnOutsideClick)
  }, [])

  const selectDate = date => {
    if (!date) return
    onChange(toIsoDate(date))
    setOpen(false)
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen(current => !current)}
        className="w-full flex items-center gap-3 bg-white/[0.035] border border-white/[0.06] rounded-[10px] text-left px-3.5 py-3 transition-all duration-200 hover:border-white/[0.14] focus:outline-none focus:border-green focus:ring-2 focus:ring-green/10"
        aria-expanded={open}
      >
        <span className="w-8 h-8 rounded-[8px] bg-green/10 text-green flex items-center justify-center text-base">▣</span>
        <span className="flex-1 min-w-0">
          <span className="block text-[10px] uppercase tracking-[1.4px] text-muted">Selected date</span>
          <span className="block text-sm font-bold text-text mt-0.5">
            {selected ? format(selected, 'EEEE, MMMM d, yyyy') : 'Choose match date'}
          </span>
        </span>
        <span className={`text-muted text-xs transition-transform ${open ? 'rotate-180' : ''}`}>▼</span>
      </button>

      {open && (
        <div className="match-date-popover absolute left-0 top-[calc(100%+8px)] z-[300] rounded-[14px] border border-white/[0.1] bg-card shadow-2xl p-3">
          <DayPicker
            mode="single"
            selected={selected}
            defaultMonth={selected}
            onSelect={selectDate}
            showOutsideDays
            fixedWeeks
          />
          <div className="border-t border-white/[0.06] pt-2 mt-1 flex justify-between items-center">
            <span className="text-[10px] text-muted">History before selected date</span>
            <button
              type="button"
              onClick={() => selectDate(new Date())}
              className="text-[11px] font-bold text-green px-2.5 py-1.5 rounded-[7px] bg-green/10 hover:bg-green/20 transition-colors"
            >
              Today
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
