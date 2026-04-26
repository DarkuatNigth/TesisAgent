"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { BrainCircuit, LayoutList, Home, Bot } from "lucide-react";
import AgentChat from "./AgentChat";

export default function Navbar() {
  const path = usePathname();
  const [chatOpen, setChatOpen] = useState(false);

  const links = [
    { href: "/presentacion", label: "Presentación", icon: Home },
    { href: "/listado",      label: "Listado",       icon: LayoutList },
  ];

  return (
    <>
      <nav className="sticky top-0 z-40 border-b border-gray-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <BrainCircuit size={22} className="text-indigo-600" />
            <span className="text-sm font-medium text-gray-900">InnoTech</span>
          </div>

          {/* Links */}
          <div className="flex items-center gap-1">
            {links.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors
                  ${path === href
                    ? "bg-indigo-50 text-indigo-700 font-medium"
                    : "text-gray-500 hover:text-gray-900 hover:bg-gray-100"
                  }`}
              >
                <Icon size={15} />
                {label}
              </Link>
            ))}
          </div>

          {/* Botón agente */}
          <button
            onClick={() => setChatOpen(true)}
            className="flex items-center gap-2 rounded-full bg-indigo-600 px-4 py-1.5
                       text-sm font-medium text-white transition hover:bg-indigo-700 active:scale-95"
          >
            <Bot size={15} />
            Agente IA
          </button>
        </div>
      </nav>

      {/* Panel de chat */}
      {chatOpen && <AgentChat onClose={() => setChatOpen(false)} />}
    </>
  );
}