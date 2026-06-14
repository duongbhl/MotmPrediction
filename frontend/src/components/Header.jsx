export default function Header() {
  return (
    <header className="sticky top-0 z-[200] border-b border-white/[0.06] bg-bg/[0.92] backdrop-blur-2xl">
      <div className="max-w-[1360px] mx-auto px-7 flex items-center justify-between h-16">

        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-[38px] h-[38px] rounded-[10px] bg-gradient-to-br from-green to-[#00B8FF] flex items-center justify-center text-[19px] shadow-[0_0_18px_rgba(0,232,122,0.28)]">
            ⚽
          </div>
          <div>
            <div className="text-[17px] font-black tracking-tight bg-gradient-to-r from-green to-[#00B8FF] bg-clip-text text-transparent">
              MOTM PREDICTOR
            </div>
            <div className="text-[11px] text-muted uppercase tracking-[1.8px]">
              Premier League · AI Analytics
            </div>
          </div>
        </div>

        {/* Right */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-[7px] px-3.5 py-1.5 rounded-full border border-green/[0.18] bg-green/10 text-[12px] font-semibold text-green tracking-[0.3px]">
            <span className="w-[7px] h-[7px] rounded-full bg-green [animation:livePulse_2s_ease_infinite]" />
            AI Powered
          </div>
          <div className="px-3.5 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.06] text-xs text-dim">
            Pre-match
          </div>
        </div>

      </div>
    </header>
  )
}
