"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-03 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Accounts
    op.create_table(
        'accounts',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('platform', sa.String(length=50), nullable=False, server_default='tiktok'),
        sa.Column('open_id', sa.String(length=255), nullable=False),
        sa.Column('union_id', sa.String(length=255), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=150), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('refresh_expires_at', sa.DateTime(), nullable=True),
        sa.Column('scopes', sa.String(length=255), nullable=False, server_default='user.info.basic,video.publish'),
        sa.Column('privacy_options', sa.Text(), nullable=True),
        sa.Column('comment_disabled', sa.Boolean(), server_default='0'),
        sa.Column('duet_disabled', sa.Boolean(), server_default='0'),
        sa.Column('stitch_disabled', sa.Boolean(), server_default='0'),
        sa.Column('max_video_duration_sec', sa.String(length=20), server_default='600'),
        sa.Column('is_active', sa.Boolean(), server_default='1'),
        sa.Column('is_eligible', sa.Boolean(), server_default='0'),
        sa.Column('eligibility_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )
    op.create_index(op.f('ix_accounts_open_id'), 'accounts', ['open_id'], unique=True)

    # 2. Drive Sources
    op.create_table(
        'drive_sources',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('folder_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('include_subfolders', sa.Boolean(), server_default='0'),
        sa.Column('sync_interval_minutes', sa.Integer(), server_default='15'),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('sync_page_token', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )
    op.create_index(op.f('ix_drive_sources_folder_id'), 'drive_sources', ['folder_id'], unique=True)

    # 3. Media Assets
    op.create_table(
        'media_assets',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('drive_source_id', sa.String(length=36), sa.ForeignKey('drive_sources.id'), nullable=True),
        sa.Column('drive_file_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=100), server_default='video/mp4'),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('md5_checksum', sa.String(length=64), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('aspect_ratio', sa.String(length=20), nullable=True),
        sa.Column('video_codec', sa.String(length=50), nullable=True),
        sa.Column('audio_codec', sa.String(length=50), nullable=True),
        sa.Column('has_audio', sa.String(length=10), server_default='yes'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DISCOVERED'),
        sa.Column('validation_notes', sa.Text(), nullable=True),
        sa.Column('local_storage_path', sa.String(length=500), nullable=True),
        sa.Column('thumbnail_path', sa.String(length=500), nullable=True),
        sa.Column('drive_modified_time', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )
    op.create_index(op.f('ix_media_assets_drive_file_id'), 'media_assets', ['drive_file_id'], unique=True)
    op.create_index(op.f('ix_media_assets_sha256_hash'), 'media_assets', ['sha256_hash'])

    # 4. Post Drafts
    op.create_table(
        'post_drafts',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('media_asset_id', sa.String(length=36), sa.ForeignKey('media_assets.id'), nullable=False),
        sa.Column('account_id', sa.String(length=36), sa.ForeignKey('accounts.id'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('caption', sa.Text(), nullable=False, server_default=''),
        sa.Column('hashtags', sa.String(length=255), nullable=True),
        sa.Column('privacy_level', sa.String(length=50), server_default='SELF_ONLY'),
        sa.Column('disable_comment', sa.Boolean(), server_default='0'),
        sa.Column('disable_duet', sa.Boolean(), server_default='0'),
        sa.Column('disable_stitch', sa.Boolean(), server_default='0'),
        sa.Column('is_aigc', sa.Boolean(), server_default='0'),
        sa.Column('brand_content_toggle', sa.Boolean(), server_default='0'),
        sa.Column('brand_organic_toggle', sa.Boolean(), server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('validation_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )

    # 5. Approvals
    op.create_table(
        'approvals',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('post_draft_id', sa.String(length=36), sa.ForeignKey('post_drafts.id'), nullable=False),
        sa.Column('approved_by', sa.String(length=100), server_default='operador'),
        sa.Column('approved_at', sa.DateTime(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revocation_reason', sa.String(length=255), nullable=True)
    )

    # 6. Scheduled Posts
    op.create_table(
        'scheduled_posts',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('post_draft_id', sa.String(length=36), sa.ForeignKey('post_drafts.id'), nullable=False),
        sa.Column('account_id', sa.String(length=36), sa.ForeignKey('accounts.id'), nullable=True),
        sa.Column('scheduled_time_utc', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='SCHEDULED', nullable=False),
        sa.Column('lock_id', sa.String(length=64), nullable=True),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.Column('priority', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )
    op.create_index(op.f('ix_scheduled_posts_scheduled_time_utc'), 'scheduled_posts', ['scheduled_time_utc'])

    # 7. Publish Attempts
    op.create_table(
        'publish_attempts',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('scheduled_post_id', sa.String(length=36), sa.ForeignKey('scheduled_posts.id'), nullable=False),
        sa.Column('attempt_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('publish_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('raw_response', sa.Text(), nullable=True)
    )
    op.create_index(op.f('ix_publish_attempts_publish_id'), 'publish_attempts', ['publish_id'])

    # 8. Audit Events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=True),
        sa.Column('user_or_system', sa.String(length=100), server_default='system'),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_index(op.f('ix_audit_events_created_at'), 'audit_events', ['created_at'])


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('publish_attempts')
    op.drop_table('scheduled_posts')
    op.drop_table('approvals')
    op.drop_table('post_drafts')
    op.drop_table('media_assets')
    op.drop_table('drive_sources')
    op.drop_table('accounts')
