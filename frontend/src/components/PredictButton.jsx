export default function PredictButton({ loading, onClick }) {
  return (
    <div className="flex flex-col items-center gap-3 my-5">
      <button
        onClick={onClick}
        disabled={loading}
        className={[
          'relative flex items-center justify-center gap-2.5',
          'px-10 py-[15px] rounded-[14px]',
          'text-[15px] font-extrabold tracking-[0.5px]',
          'transition-all duration-300',
          loading
            ? 'bg-white/[0.06] text-dim cursor-not-allowed'
            : 'bg-gradient-to-r from-green to-[#00B8FF] text-[#06090F] cursor-pointer shadow-[0_0_28px_rgba(0,232,122,0.35)] hover:shadow-[0_0_40px_rgba(0,232,122,0.50)] hover:-translate-y-[2px]',
        ].join(' ')}
      >
        {loading ? (
          <>
            <span className="w-[18px] h-[18px] border-2 border-dim border-t-transparent rounded-full [animation:spinA_0.7s_linear_infinite]" />
            Analyzing…
          </>
        ) : (
          <><span>⚡</span> Analyze &amp; Predict MOTM</>
        )}
      </button>
      <p className="text-xs text-muted text-center">
        Enter player stats above, then click to reveal the Man of the Match
      </p>
    </div>
  )
}

