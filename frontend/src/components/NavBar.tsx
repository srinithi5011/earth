import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/scientist", label: "AI Environmental Scientist" },
  { to: "/profile", label: "Environmental Profile" },
  { to: "/evidence", label: "Evidence Explorer" },
  { to: "/reasoning", label: "Reasoning Graph" },
];

export default function NavBar() {
  return (
    <aside className="w-64 shrink-0 border-r border-emerald-100 bg-white h-screen sticky top-0 flex flex-col justify-between shadow-xs z-30">
      <div>
        <div className="px-6 py-6 border-b border-emerald-100/60 flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-emerald-700 flex items-center justify-center text-white font-bold shadow-xs">
            D
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-slate-900 leading-none">
              DARUKAA EARTH
            </h1>
            <p className="text-[10px] text-emerald-800 font-semibold tracking-wide mt-1">
              AI Biodiversity Intelligence
            </p>
          </div>
        </div>

        <nav className="px-3 py-4 flex flex-col gap-1">
          {LINKS.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                `text-xs font-semibold px-4 py-3 rounded-xl transition-all duration-150 ${
                  isActive
                    ? "bg-emerald-50 text-emerald-900 border border-emerald-200/80 shadow-2xs"
                    : "text-slate-600 hover:bg-slate-50 hover:text-emerald-800"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="p-4 border-t border-emerald-100/60 text-[11px] text-slate-400 font-medium text-center">
        Engine Version 1.0.4 · Evidence Grounded
      </div>
    </aside>
  );
}