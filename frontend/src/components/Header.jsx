import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { logout } from "../features/auth/authSlice.js";
import { ChevronDown, Building2 } from "./icons.jsx";

export default function Header({ activeView, onViewChange, onShowToast }) {
  const dispatch = useDispatch();
  const { user } = useSelector((s) => s.auth);
  
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [companyMenuOpen, setCompanyMenuOpen] = useState(false);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (!e.target.closest("#company-menu") && !e.target.closest("#company-menu-button")) {
        setCompanyMenuOpen(false);
      }
      if (!e.target.closest("#user-menu") && !e.target.closest("#user-menu-button")) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSignOut = () => {
    dispatch(logout());
  };

  const getInitials = (name) => {
    if (!name) return "U";
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
  };

  const isMfgActive = ["batches", "raw_materials", "process_checks", "manufacturing"].includes(activeView);
  const isInvActive = ["investigation", "root_cause"].includes(activeView);
  const isCapaActive = ["capa", "effectiveness"].includes(activeView);

  const navItems = [
    { id: "dashboard", label: "Dashboard", active: activeView === "dashboard", target: "dashboard" },
    { id: "manufacturing", label: "Manufacturing", active: isMfgActive, target: "batches" },
    { id: "deviations", label: "Deviations", active: activeView === "deviations", target: "deviations" },
    { id: "investigation", label: "Investigation", active: isInvActive, target: "investigation" },
    { id: "capa", label: "CAPA", active: isCapaActive, target: "capa" },
    { id: "batch_release", label: "Batch Release", active: activeView === "batch_release", target: "batch_release" },
    { id: "audit_trail", label: "Audit Trail", active: activeView === "audit_trail", target: "audit_trail" },
    { id: "complaints", label: "Complaints", active: activeView === "complaints", target: "complaints" },
  ];

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white shadow-xs">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Left: Brand + 8 Primary Navigation Items */}
        <div className="flex items-center gap-5 sm:gap-6 min-w-0">
          {/* Logo Area */}
          <button 
            type="button"
            onClick={() => onViewChange("dashboard")}
            className="flex items-center gap-2 shrink-0 cursor-pointer focus:outline-none text-left"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white font-bold text-sm shadow-xs">
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
            </div>
            <div className="flex flex-col">
              <span className="text-sm sm:text-base font-bold tracking-tight text-slate-900 leading-none">PharmaOne-AI</span>
              <span className="text-[9px] font-semibold text-blue-600 uppercase tracking-wider mt-0.5">Enterprise QMS</span>
            </div>
          </button>

          {/* Primary Navbar: Clean flex with equal spacing */}
          <nav className="hidden md:flex items-center space-x-1" aria-label="Primary Navigation">
            {navItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onViewChange(item.target)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
                  item.active
                    ? "bg-blue-50 text-blue-700 font-semibold border border-blue-200/60 shadow-2xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/70"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Right side: Visual Divider + Company Selector, Notifications, User Menu */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="hidden sm:block h-5 w-px bg-slate-200" aria-hidden="true" />

          {/* Active Company & Site Selector */}
          <div className="relative">
            <button
              type="button"
              id="company-menu-button"
              onClick={() => setCompanyMenuOpen(!companyMenuOpen)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50/80 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-100 transition-colors focus:outline-none"
              aria-expanded={companyMenuOpen}
            >
              <Building2 className="h-3.5 w-3.5 text-blue-600 shrink-0" />
              <span className="font-semibold text-slate-800 text-[11px] truncate max-w-[130px] sm:max-w-[160px]" title="Vasundha Pharma Chem Limited (Bengaluru)">
                {user?.company_name || "Vasundha Pharma"}
              </span>
              <ChevronDown className="h-3 w-3 text-slate-400 shrink-0" />
            </button>

            {companyMenuOpen && (
              <div id="company-menu" className="absolute right-0 mt-2 w-64 origin-top-right rounded-lg border border-slate-200 bg-white py-1 shadow-lg ring-1 ring-black/5 focus:outline-none z-50">
                <div className="px-3 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  Active Site & Organization
                </div>
                <div className="px-3 py-2 flex items-center justify-between text-xs text-slate-800 bg-blue-50/60 font-medium">
                  <div className="truncate">
                    <strong className="block">{user?.company_name || "Vasundha Pharma Chem Limited"}</strong>
                    <span className="text-[10px] text-slate-500">Site: Bengaluru · Sterile & API</span>
                  </div>
                  <span className="ml-2 text-[10px] text-blue-700 bg-blue-100 rounded px-1.5 py-0.5 font-semibold">Active</span>
                </div>
              </div>
            )}
          </div>

          {/* Notification Bell */}
          <button
            type="button"
            className="relative rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus:outline-none transition-colors"
            aria-label="Notifications"
            onClick={() => onShowToast && onShowToast("1 urgent: Process excursion on Batch API-2026-041")}
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            <span className="absolute top-1 right-1 h-1.5 w-1.5 rounded-full bg-blue-500 ring-2 ring-white" />
          </button>

          {/* User Menu / Avatar */}
          <div className="relative">
            <button
              type="button"
              id="user-menu-button"
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-2 rounded-full focus:outline-none"
              aria-expanded={userMenuOpen}
            >
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-blue-700 text-xs font-bold border border-blue-200">
                {getInitials(user?.full_name || "Priyanshu")}
              </div>
              <div className="hidden lg:block text-left text-xs">
                <div className="font-semibold text-slate-800 leading-tight">{user?.full_name || "Priyanshu"}</div>
                <div className="text-[10px] text-slate-400 font-medium leading-none">{user?.role || "QA Manager"}</div>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-slate-400 hidden lg:block" />
            </button>

            {userMenuOpen && (
              <div id="user-menu" className="absolute right-0 mt-2 w-56 origin-top-right rounded-lg border border-slate-200 bg-white py-1 shadow-lg ring-1 ring-black/5 focus:outline-none z-50">
                <div className="border-b border-slate-100 px-4 py-2.5">
                  <p className="text-xs font-semibold text-slate-800">{user?.full_name || "Priyanshu"}</p>
                  <p className="text-[11px] text-slate-500 truncate">{user?.email || "priyanshu@gmail.com"}</p>
                  <span className="inline-block mt-1 text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono">
                    Role: {user?.role || "QA Manager"}
                  </span>
                </div>

                <div className="border-t border-slate-100 py-1">
                  <button
                    type="button"
                    onClick={handleSignOut}
                    className="block w-full px-4 py-2 text-left text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
                  >
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
