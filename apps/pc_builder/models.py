from django.db import models


class Cpu(models.Model):
    name = models.TextField()
    price = models.FloatField()
    core_count = models.IntegerField()
    core_clock = models.FloatField()
    boost_clock = models.FloatField()
    microarchitecture = models.TextField()
    tdp = models.IntegerField()
    graphics = models.IntegerField()
    brand_en = models.TextField(null=True)
    brand = models.TextField(null=True)
    socket_hint = models.TextField(null=True)
    socket = models.TextField(null=True)
    threads = models.IntegerField(null=True)
    l3_cache_mb = models.IntegerField(null=True)

    class Meta:
        db_table = "cpu"
        managed = False

    def __str__(self):
        return self.name


class Gpu(models.Model):
    name = models.TextField()
    price = models.FloatField()
    chipset = models.TextField()
    memory = models.FloatField()
    core_clock = models.FloatField()
    boost_clock = models.FloatField()
    length = models.FloatField()
    brand_en = models.TextField(null=True)
    brand = models.TextField(null=True)
    gpu_vendor = models.TextField(null=True)
    tdp = models.IntegerField(null=True)
    chip_vendor = models.TextField(null=True)
    length_class = models.TextField(null=True)

    class Meta:
        db_table = "gpu"
        managed = False

    def __str__(self):
        return self.name


class Mb(models.Model):
    name = models.TextField()
    price = models.FloatField()
    socket = models.TextField()
    form_factor = models.TextField()
    max_memory = models.IntegerField()
    memory_slots = models.IntegerField()
    brand_en = models.TextField(null=True)
    brand = models.TextField(null=True)
    ddr_generation = models.TextField(null=True)
    m2_slots = models.IntegerField(null=True)

    class Meta:
        db_table = "mb"
        managed = False

    def __str__(self):
        return self.name


class Ram(models.Model):
    name = models.TextField()
    price = models.FloatField()
    speed = models.TextField()
    modules = models.TextField()
    first_word_latency = models.FloatField()
    cas_latency = models.FloatField()
    brand_en = models.TextField(null=True)
    brand = models.TextField(null=True)
    module_count = models.IntegerField(null=True)
    module_size_gb = models.FloatField(null=True)
    total_capacity_gb = models.FloatField(null=True)
    ddr_generation = models.TextField(null=True)

    class Meta:
        db_table = "ram"
        managed = False

    def __str__(self):
        return self.name


class Psu(models.Model):
    name = models.TextField()
    price = models.FloatField()
    type = models.TextField()
    efficiency = models.TextField()
    wattage = models.IntegerField()
    modular = models.TextField()
    brand_en = models.TextField(null=True)
    brand = models.TextField(null=True)
    efficiency_score = models.IntegerField(null=True)
    atx_version = models.TextField(null=True)

    class Meta:
        db_table = "psu"
        managed = False

    def __str__(self):
        return self.name


class Case(models.Model):
    name = models.TextField()
    price = models.FloatField()
    type = models.TextField()
    external_volume = models.FloatField()
    internal_35_bays = models.IntegerField()
    brand_en = models.TextField(null=True)
    brand = models.TextField(null=True)
    max_gpu_length = models.IntegerField(null=True)
    max_cooler_height = models.IntegerField(null=True)

    class Meta:
        db_table = "case"
        managed = False

    def __str__(self):
        return self.name


class Storage(models.Model):
    name = models.TextField()
    price = models.FloatField()
    capacity = models.FloatField()
    type = models.TextField()
    cache = models.FloatField()
    form_factor = models.TextField()
    interface = models.TextField()
    brand_en = models.TextField(null=True)
    brand = models.TextField(null=True)
    storage_class = models.TextField(null=True)
    is_nvme = models.IntegerField(null=True)
    tbw = models.IntegerField(null=True)

    class Meta:
        db_table = "storage"
        managed = False

    def __str__(self):
        return self.name


class CpuCooler(models.Model):
    name = models.TextField()
    price = models.FloatField()
    rpm = models.TextField()
    noise_level = models.TextField()
    size = models.FloatField()
    brand_en = models.TextField(null=True)
    brand = models.TextField(null=True)
    cooler_type = models.TextField(null=True)
    tdp_capacity = models.IntegerField(null=True)
    socket_support = models.TextField(null=True)

    class Meta:
        db_table = "cpu_cooler"
        managed = False

    def __str__(self):
        return self.name
