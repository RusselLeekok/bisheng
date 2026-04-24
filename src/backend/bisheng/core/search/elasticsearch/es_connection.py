from typing import Optional

from elasticsearch import Elasticsearch, AsyncElasticsearch


class ElasticsearchHostsNotConfiguredError(ValueError):
    """Raised when Elasticsearch hosts are missing from configuration."""


class ESConnection:
    def __init__(self, es_hosts: str, **kwargs):
        self.es_hosts = es_hosts
        self.es_kwargs = kwargs

        self._sync_es_connection: Optional[Elasticsearch] = None
        self._es_connection: Optional[AsyncElasticsearch] = None

    def _validate_hosts(self):
        if not self.es_hosts:
            raise ElasticsearchHostsNotConfiguredError("Elasticsearch hosts are not configured")

    def _create_es_connection(self) -> 'AsyncElasticsearch':
        self._validate_hosts()
        return AsyncElasticsearch(
            hosts=self.es_hosts,
            **self.es_kwargs
        )

    def _create_sync_es_connection(self) -> 'Elasticsearch':
        self._validate_hosts()
        return Elasticsearch(
            hosts=self.es_hosts,
            **self.es_kwargs
        )

    @property
    def es_connection(self) -> 'AsyncElasticsearch':
        if self._es_connection is None:
            self._es_connection = self._create_es_connection()
        return self._es_connection

    @property
    def sync_es_connection(self) -> 'Elasticsearch':
        if self._sync_es_connection is None:
            self._sync_es_connection = self._create_sync_es_connection()
        return self._sync_es_connection

    async def close(self):
        if self._es_connection is not None:
            await self._es_connection.close()
            self._es_connection = None

    def sync_close(self):
        if self._sync_es_connection is not None:
            self._sync_es_connection.close()
            self._sync_es_connection = None
