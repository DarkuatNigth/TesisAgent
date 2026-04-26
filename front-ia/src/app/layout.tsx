import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "InnoTech — Análisis de Rendimiento",
  description: "Sistema de análisis y recuperación académica con IA",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className={geist.className}>
        <Navbar />
        <main className="min-h-screen bg-gray-50">{children}</main>
      </body>
    </html>
  );
}