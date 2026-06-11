import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

describe("Admin App", () => {
  it("renders without crashing", () => {
    const { container } = render(<App />);
    expect(container).toBeTruthy();
  });

  it("renders the App container", () => {
    const { container } = render(<App />);
    const appDiv = container.querySelector(".App");
    expect(appDiv).toBeInTheDocument();
  });
});
