import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from api.fetcher import extract_api_token
from main import _choose_numbers, _choose_quality, _parse_number_selection
from utils.extractor import (
    add_hls_quality_options,
    extract_episode_info,
    fetch_metadata_async,
    fetch_metadata_and_stream_data,
    list_quality_options,
)
from utils.url_utils import find_season_numbers, find_video_urls, get_id_from_url
from utils.validate import validate_url


class UrlTests(unittest.TestCase):
    def test_current_and_legacy_urls_are_supported(self):
        self.assertTrue(
            validate_url("https://www.zdf.de/filme/bis-es-blutet-movie-100")
        )
        self.assertTrue(
            validate_url("https://www.zdf.de/serien/show/episode-100.html")
        )
        self.assertFalse(validate_url("https://www.zdf.de.evil.example/video-100"))

    def test_content_id_ignores_query_and_optional_html_suffix(self):
        self.assertEqual(
            get_id_from_url("https://www.zdf.de/video/example-100?foo=bar"),
            "video/example-100",
        )
        self.assertEqual(
            get_id_from_url("https://www.zdf.de/serien/show/episode-100.html"),
            "serien/show/episode-100",
        )

    def test_collection_only_returns_its_own_video_urls(self):
        page_url = "https://www.zdf.de/serien/example-100"
        episode = "https://www.zdf.de/video/serien/example-100/episode-1-100"
        html = f'{episode}\\" {episode}\\" https://www.zdf.de/video/serien/other-100/trailer-100\\"'
        self.assertEqual(find_video_urls(page_url, html), [episode])

    def test_finds_all_season_tabs(self):
        html = "Staffel 4 ... Staffel 1 ... Staffel 3 ... Staffel 2"
        self.assertEqual(find_season_numbers(html), [1, 2, 3, 4])

    def test_number_selection_supports_lists_ranges_and_all(self):
        available = [1, 2, 3, 4, 5]
        self.assertEqual(_parse_number_selection("1,3-4", available), [1, 3, 4])
        self.assertEqual(_parse_number_selection("all", available), available)
        with self.assertRaisesRegex(ValueError, "Unavailable"):
            _parse_number_selection("6", available)

    @patch("builtins.input", side_effect=EOFError)
    @patch("main.sys.stdin.isatty", return_value=True)
    def test_number_selection_uses_default_on_eof(self, _isatty, _input):
        self.assertEqual(_choose_numbers("seasons", [1, 2, 3], "2", None), [2])


class ApiTests(unittest.TestCase):
    def test_extracts_current_escaped_video_token(self):
        html = r'{\"videoToken\":{\"apiToken\":\"test-token-123\"}}'
        self.assertEqual(extract_api_token(html), "test-token-123")

    def test_extracts_season_and_episode_from_programme_metadata(self):
        metadata = {
            "programmeItem": [
                {
                    "http://zdf.de/rels/target": {
                        "episodeNumber": 4,
                        "http://zdf.de/rels/cmdm/season": {"seasonNumber": 1},
                    }
                }
            ]
        }
        self.assertEqual(extract_episode_info(metadata), (1, 4))

    @patch("utils.extractor.fetch_json")
    def test_follows_content_redirect_and_uses_ptmd_template(self, fetch_json):
        metadata = {
            "title": "Example",
            "mainVideoContent": {
                "http://zdf.de/rels/target": {
                    "streams": {
                        "default": {
                            "http://zdf.de/rels/streams/ptmd-template": (
                                "/tmd/2/{playerId}/vod/ptmd/mediathek/example/4"
                            )
                        }
                    }
                }
            },
        }
        stream_data = {"priorityList": []}
        fetch_json.side_effect = [
            {
                "profile": "http://zdf.de/rels/moved-permanently",
                "location": "/content/documents/zdf/new/example-100.json",
            },
            metadata,
            stream_data,
        ]

        result = fetch_metadata_and_stream_data(
            "https://www.zdf.de/video/example-100", {"Api-Auth": "Bearer token"}
        )

        self.assertEqual(result, (metadata, stream_data))
        self.assertEqual(
            fetch_json.call_args_list[2].args[0],
            "https://api.zdf.de/tmd/2/ngplayer_2_4/vod/ptmd/mediathek/example/4",
        )

    def test_quality_selection_prefers_progressive_mp4_main_track(self):
        def form(mime_type, adaptive, uri, track_class="main"):
            return {
                "mimeType": mime_type,
                "isAdaptive": adaptive,
                "qualities": [
                    {
                        "quality": "high",
                        "audio": {
                            "tracks": [{"class": track_class, "uri": uri}]
                        },
                    }
                ],
            }

        stream_data = {
            "priorityList": [
                {
                    "formitaeten": [
                        form("video/webm", False, "https://example/high.webm"),
                        form(
                            "application/x-mpegURL",
                            True,
                            "https://example/master.m3u8",
                        ),
                        form("video/mp4", False, "https://example/high.mp4"),
                    ]
                }
            ]
        }

        self.assertEqual(
            list_quality_options(stream_data),
            {"high": "https://example/high.mp4"},
        )

    @patch("utils.extractor.fetch_page")
    def test_hls_qualities_use_real_resolution_and_frame_rate(self, fetch_page):
        fetch_page.return_value = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=3429496,RESOLUTION=1280x720,FRAME-RATE=50.000
720.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=6990968,RESOLUTION=1920x1080,FRAME-RATE=50.000
1080.m3u8
"""
        result = add_hls_quality_options(
            {
                "auto": "https://example/master.m3u8",
                "veryhigh": "https://example/video.mp4",
            }
        )
        self.assertEqual(
            result,
            {
                "1080p50": "https://example/1080.m3u8",
                "720p50": "https://example/720.m3u8",
                "veryhigh": "https://example/video.mp4",
            },
        )

    @patch("builtins.input", return_value="")
    @patch("main.sys.stdin.isatty", return_value=True)
    def test_interactive_default_is_highest_quality(self, _isatty, _input):
        args = SimpleNamespace(best=False, quality=None)
        selected = _choose_quality(
            {
                "1080p50": "https://example/1080.m3u8",
                "veryhigh": "https://example/video.mp4",
            },
            args,
        )
        self.assertEqual(selected, "1080p50")
        self.assertTrue(args.best)
        self.assertEqual(
            _choose_quality(
                {
                    "1080p50": "https://example/1080.m3u8",
                    "720p50": "https://example/720.m3u8",
                },
                args,
            ),
            "1080p50",
        )


class AsyncApiTests(unittest.IsolatedAsyncioTestCase):
    @patch("utils.extractor.fetch_json_async", new_callable=AsyncMock)
    async def test_async_metadata_follows_content_redirect(self, fetch_json_async):
        metadata = {"title": "Example"}
        fetch_json_async.side_effect = [
            {
                "profile": "http://zdf.de/rels/moved-permanently",
                "location": "/content/documents/zdf/new/example-100.json",
            },
            metadata,
        ]

        result = await fetch_metadata_async(
            "https://www.zdf.de/video/example-100",
            {"Api-Auth": "Bearer token"},
            object(),
        )

        self.assertEqual(result, metadata)
        self.assertEqual(
            fetch_json_async.await_args_list[1].args[0],
            "https://api.zdf.de/content/documents/zdf/new/example-100.json",
        )


if __name__ == "__main__":
    unittest.main()
