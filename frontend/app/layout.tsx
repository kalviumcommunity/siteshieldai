import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Site Shield AI — Construction Regulatory Compliance Assistant",
  description:
    "Grounded construction compliance assistant providing strict citation validation, conflict detection, and safety abstention.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
