import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Video Clipper",
  description: "Ekstrak klip menarik dari video panjang (stream gaming, podcast).",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
