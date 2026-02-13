import { beforeEach, describe, expect, test, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../src/App'

const setupGlobalMocks = () => {
  const fetchMock = vi.fn()
  fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/warmup')) {
      return { ok: true, json: async () => ({ ok: true }) } as Response
    }
    return { ok: true, json: async () => ({}) } as Response
  })
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('alert', vi.fn())
  vi.stubGlobal('confirm', vi.fn(() => true))
  vi.stubGlobal('URL', {
    ...URL,
    createObjectURL: vi.fn(() => 'blob:mock'),
    revokeObjectURL: vi.fn(),
  })
  return fetchMock
}

const moveToCaptureView = async () => {
  const user = userEvent.setup()
  await screen.findByText(/event configuration/i)
  await user.type(
    screen.getByPlaceholderText(/workshop registration/i),
    'Reliability Event'
  )
  await user.click(screen.getByRole('button', { name: /initialize session/i }))
  return user
}

describe('App critical flow', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  test('routes to review first before extraction call', async () => {
    const fetchMock = setupGlobalMocks()
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/warmup')) {
        return { ok: true, json: async () => ({ ok: true }) } as Response
      }
      if (url.endsWith('/extract')) {
        return {
          ok: true,
          json: async () => ({
            table: {
              headers: ['Name', 'Phone'],
              rows: [{ Name: 'Ada', Phone: '123' }],
            },
          }),
        } as Response
      }
      return { ok: true, json: async () => ({}) } as Response
    })

    const { container } = render(<App />)
    const user = await moveToCaptureView()

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['image-bytes'], 'register.jpg', { type: 'image/jpeg' })
    await user.upload(fileInput, file)

    expect(await screen.findByText(/review before extraction/i)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/warmup'),
      expect.objectContaining({ method: 'POST' })
    )

    await user.click(screen.getByRole('button', { name: /proceed to extraction/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/extract'),
        expect.objectContaining({ method: 'POST' })
      )
    })
    expect(await screen.findByText(/verify data/i)).toBeInTheDocument()
  })

  test('retake from review returns to capture and does not call extract', async () => {
    const fetchMock = setupGlobalMocks()
    const { container } = render(<App />)
    const user = await moveToCaptureView()

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['image-bytes'], 'register.jpg', { type: 'image/jpeg' })
    await user.upload(fileInput, file)

    expect(await screen.findByText(/review before extraction/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /retake/i }))

    expect(await screen.findByText(/upload register/i)).toBeInTheDocument()
    const extractCalls = fetchMock.mock.calls.filter((call) => String(call[0]).includes('/extract'))
    expect(extractCalls).toHaveLength(0)
  })

  test('loads history and renders exported rows in app', async () => {
    const fetchMock = setupGlobalMocks()
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/warmup')) {
        return { ok: true, json: async () => ({ ok: true }) } as Response
      }
      if (url.includes('/exports/Reliability%20Event/exp-1')) {
        return {
          ok: true,
          json: async () => ({
            eventName: 'Reliability Event',
            exportId: 'exp-1',
            rowCount: 1,
            rows: [{ name: 'Ada', phone: '123' }],
          }),
        } as Response
      }
      if (url.includes('/exports/Reliability%20Event')) {
        return {
          ok: true,
          json: async () => ({
            eventName: 'Reliability Event',
            exports: [
              { export_id: 'exp-1', exported_at: '2026-02-13T12:00:00Z', row_count: 1 },
            ],
          }),
        } as Response
      }
      return { ok: true, json: async () => ({}) } as Response
    })

    render(<App />)
    const user = await moveToCaptureView()

    await user.click(screen.getByRole('button', { name: /view history/i }))

    expect(await screen.findByText(/export history/i)).toBeInTheDocument()
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/exports/Reliability%20Event')
      )
    })
    expect(await screen.findByText('Ada')).toBeInTheDocument()
  })
})
