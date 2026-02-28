from modules.auto_tasks import nsfw_image_case_review as img_scan_tasks
from unittest.mock import patch
import pytest



@pytest.mark.asyncio
async def test_handle_task_upvote_whitelists_when_upvotes_greater():
    fake_messages = [
        {"img_hash": "hash1", "upvotes": 5, "downvotes": 1},
    ]

    with patch("modules.auto_tasks.nsfw_image_case_review.nsfw_scanner_reviews.list_review_msgs") as mock_list, \
         patch("modules.auto_tasks.nsfw_image_case_review.nsfw_scanner.whitelist_image") as mock_whitelist, \
         patch("modules.auto_tasks.nsfw_image_case_review.nsfw_scanner.blacklist_image") as mock_blacklist:

        mock_list.return_value = fake_messages

        await img_scan_tasks.handle_task(for_upvote=True)

        mock_list.assert_called_once_with(min_upvotes=img_scan_tasks.vote_threshold)
        mock_whitelist.assert_called_once_with("hash1")
        mock_blacklist.assert_not_called()


@pytest.mark.asyncio
async def test_handle_task_upvote_blacklists_when_downvotes_greater():
    fake_messages = [
        {"img_hash": "hash2", "upvotes": 1, "downvotes": 5},
    ]

    with patch("modules.auto_tasks.nsfw_image_case_review.nsfw_scanner_reviews.list_review_msgs") as mock_list, \
         patch("modules.auto_tasks.nsfw_image_case_review.nsfw_scanner.whitelist_image") as mock_whitelist, \
         patch("modules.auto_tasks.nsfw_image_case_review.nsfw_scanner.blacklist_image") as mock_blacklist:

        mock_list.return_value = fake_messages

        await img_scan_tasks.handle_task(for_upvote=True)

        mock_blacklist.assert_called_once_with("hash2")
        mock_whitelist.assert_not_called()


@pytest.mark.asyncio
async def test_handle_task_downvote_whitelists_when_downvotes_greater():
    fake_messages = [
        {"img_hash": "hash3", "upvotes": 1, "downvotes": 5},
    ]

    with patch("modules.auto_tasks.nsfw_image_case_review.nsfw_scanner_reviews.list_review_msgs") as mock_list, \
         patch("modules.auto_tasks.nsfw_image_case_review.nsfw_scanner.whitelist_image") as mock_whitelist, \
         patch("modules.auto_tasks.nsfw_image_case_review.nsfw_scanner.blacklist_image") as mock_blacklist:

        mock_list.return_value = fake_messages

        await img_scan_tasks.handle_task(for_upvote=False)

        mock_list.assert_called_once_with(min_downvotes=img_scan_tasks.vote_threshold)
        mock_whitelist.assert_called_once_with("hash3")
        mock_blacklist.assert_not_called()


@pytest.mark.asyncio
async def test_handle_task_downvote_blacklists_when_upvotes_greater():
    fake_messages = [
        {"img_hash": "hash4", "upvotes": 5, "downvotes": 1},
    ]

    with patch("modules.auto_tasks.nsfw_image_case_review.nsfw_scanner_reviews.list_review_msgs") as mock_list, \
         patch("modules.auto_tasks.nsfw_image_case_review.nsfw_scanner.whitelist_image") as mock_whitelist, \
         patch("modules.auto_tasks.nsfw_image_case_review.nsfw_scanner.blacklist_image") as mock_blacklist:

        mock_list.return_value = fake_messages

        await img_scan_tasks.handle_task(for_upvote=False)

        mock_blacklist.assert_called_once_with("hash4")
        mock_whitelist.assert_not_called()