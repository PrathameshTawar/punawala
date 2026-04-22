import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import ApplicationHistory from "./ApplicationHistory";

jest.mock("../services/api", () => ({
  getMyApplications: jest.fn(),
}));

const { getMyApplications } = require("../services/api");

beforeEach(() => jest.clearAllMocks());

const MOCK_APPS = [
  {
    session_id: "LW-ABC123",
    loan_product: "personal",
    income: 50000,
    emi: 15000,
    status: "Approved",
    created_at: "2026-04-01T10:00:00",
  },
  {
    session_id: "LW-DEF456",
    loan_product: "home",
    income: 80000,
    emi: null,
    status: "Rejected",
    created_at: "2026-04-02T11:00:00",
  },
];

test("shows skeleton while loading", () => {
  getMyApplications.mockImplementation(() => new Promise(() => {}));
  render(<ApplicationHistory />);
  // Skeleton elements are rendered (they have the 'skeleton' class)
  expect(document.querySelectorAll(".skeleton").length).toBeGreaterThan(0);
});

test("renders applications after load", async () => {
  getMyApplications.mockResolvedValueOnce(MOCK_APPS);
  render(<ApplicationHistory />);

  await waitFor(() => {
    expect(screen.getByText("LW-ABC123")).toBeInTheDocument();
    expect(screen.getByText("LW-DEF456")).toBeInTheDocument();
  });
});

test("shows approved badge in green", async () => {
  getMyApplications.mockResolvedValueOnce(MOCK_APPS);
  render(<ApplicationHistory />);

  await waitFor(() => {
    const badge = screen.getByText("Approved");
    expect(badge).toHaveClass("badge-green");
  });
});

test("shows rejected badge in red", async () => {
  getMyApplications.mockResolvedValueOnce(MOCK_APPS);
  render(<ApplicationHistory />);

  await waitFor(() => {
    const badge = screen.getByText("Rejected");
    expect(badge).toHaveClass("badge-red");
  });
});

test("shows empty state when no applications", async () => {
  getMyApplications.mockResolvedValueOnce([]);
  render(<ApplicationHistory />);

  await waitFor(() =>
    expect(screen.getByText(/no applications yet/i)).toBeInTheDocument()
  );
});

test("shows error and retry button on failure", async () => {
  getMyApplications.mockRejectedValueOnce(new Error("Network error"));
  render(<ApplicationHistory />);

  await waitFor(() =>
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument()
  );
});

test("retry button reloads applications", async () => {
  getMyApplications
    .mockRejectedValueOnce(new Error("fail"))
    .mockResolvedValueOnce(MOCK_APPS);

  render(<ApplicationHistory />);

  await waitFor(() => screen.getByRole("button", { name: /retry/i }));
  await userEvent.click(screen.getByRole("button", { name: /retry/i }));

  await waitFor(() =>
    expect(screen.getByText("LW-ABC123")).toBeInTheDocument()
  );
});
