"""配件数据模型定义"""

from django.db import models


class Cpu(models.Model):
    name = models.TextField()
    brand = models.TextField(null=True)
    price = models.FloatField()
    socket = models.TextField(null=True)
    core_count = models.IntegerField(null=True)
    thread_count = models.IntegerField(null=True)
    base_clock = models.FloatField(null=True)
    boost_clock = models.FloatField(null=True)
    tdp = models.IntegerField(null=True)
    memory_type = models.TextField(null=True)
    memory_speed = models.IntegerField(null=True)
    single_score = models.FloatField(null=True)
    multi_score = models.FloatField(null=True)

    class Meta:
        db_table = "cpu"
        managed = False

    def __str__(self):
        return self.name


class Gpu(models.Model):
    name = models.TextField()
    chip_brand = models.TextField(null=True)
    card_brand = models.TextField(null=True)
    price = models.FloatField()
    length = models.FloatField(null=True)
    tdp = models.IntegerField(null=True)
    vram_size = models.IntegerField(null=True)
    core_clock = models.FloatField(null=True)
    memory_clock = models.FloatField(null=True)
    gaming_score = models.FloatField(null=True)
    compute_score = models.FloatField(null=True)
    noise_level = models.FloatField(null=True)

    class Meta:
        db_table = "gpu"
        managed = False

    def __str__(self):
        return self.name


class Mb(models.Model):
    name = models.TextField()
    brand = models.TextField(null=True)
    price = models.FloatField()
    form = models.TextField(null=True)
    socket = models.TextField(null=True)
    memory_slots = models.IntegerField(null=True)
    memory_type = models.TextField(null=True)
    memory_frequency = models.IntegerField(null=True)
    m2_slots = models.IntegerField(null=True)
    sata_ports = models.IntegerField(null=True)

    class Meta:
        db_table = "mb"
        managed = False

    def __str__(self):
        return self.name


class Ram(models.Model):
    name = models.TextField()
    brand = models.TextField(null=True)
    price = models.FloatField()
    type = models.TextField(null=True)
    capacity = models.IntegerField(null=True)
    frequency = models.IntegerField(null=True)
    latency = models.IntegerField(null=True)
    module_count = models.IntegerField(null=True)

    class Meta:
        db_table = "ram"
        managed = False

    def __str__(self):
        return self.name


class Psu(models.Model):
    name = models.TextField()
    brand = models.TextField(null=True)
    price = models.FloatField()
    form = models.TextField(null=True)
    wattage = models.IntegerField(null=True)
    efficiency = models.TextField(null=True)

    class Meta:
        db_table = "psu"
        managed = False

    def __str__(self):
        return self.name


class Case(models.Model):
    name = models.TextField()
    brand = models.TextField(null=True)
    price = models.FloatField()
    form = models.TextField(null=True)
    gpu_length = models.IntegerField(null=True)
    air_height = models.IntegerField(null=True)
    water_size = models.CharField(max_length=3, null=True)
    psu_form = models.TextField(null=True)
    storage_2_5 = models.IntegerField(null=True)
    storage_3_5 = models.IntegerField(null=True)

    class Meta:
        db_table = "case"
        managed = False

    def __str__(self):
        return self.name


class Storage(models.Model):
    name = models.TextField()
    brand = models.TextField(null=True)
    price = models.FloatField()
    type = models.TextField(null=True)
    capacity = models.IntegerField(null=True)
    cache_size = models.IntegerField(null=True)
    read_speed = models.IntegerField(null=True)
    write_speed = models.IntegerField(null=True)
    random_read_iops = models.IntegerField(null=True)
    random_write_iops = models.IntegerField(null=True)

    class Meta:
        db_table = "storage"
        managed = False

    def __str__(self):
        return self.name


class CpuCooler(models.Model):
    name = models.TextField()
    brand = models.TextField(null=True)
    price = models.FloatField()
    type = models.TextField(null=True)
    air_height = models.IntegerField(null=True)
    water_size = models.CharField(max_length=3, null=True)
    noise_level = models.FloatField(null=True)

    class Meta:
        db_table = "cpu_cooler"
        managed = False

    def __str__(self):
        return self.name
